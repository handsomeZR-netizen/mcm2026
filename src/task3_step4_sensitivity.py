import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pygam import LinearGAM, s, f, l

from task3_plot_style import apply_task3_style


def zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def logit(p: pd.Series, eps: float = 1e-6) -> pd.Series:
    p = p.clip(eps, 1 - eps)
    return np.log(p / (1 - p))


def map_industry_alt(raw: str) -> str:
    if pd.isna(raw):
        return "Other"
    val = str(raw).strip().lower()
    if any(k in val for k in ["actor", "actress", "comedian", "producer", "singer", "musician", "rapper"]):
        return "Entertainment"
    if any(k in val for k in ["athlete", "racing", "sports"]):
        return "Athlete"
    if any(k in val for k in ["tv personality", "social media", "model", "beauty", "fashion", "fitness"]):
        return "Reality-TV"
    return "Other"


def build_design(df: pd.DataFrame, use_alt_industry: bool, include_week: bool, include_trend: bool, include_cum: bool, include_judge: bool):
    df = df.copy()
    df["trend_z"] = zscore(df["performance_trend"])
    df["cum_z"] = zscore(df["cumulative_score"])

    if use_alt_industry:
        df["industry_group_alt"] = df["celebrity_industry"].map(map_industry_alt)
        industry_levels = ["Other", "Entertainment", "Athlete", "Reality-TV"]
        df["industry_group_use"] = pd.Categorical(df["industry_group_alt"], categories=industry_levels)
    else:
        industry_levels = ["Other", "Actor", "Singer", "Athlete", "Reality-TV"]
        df["industry_group_use"] = pd.Categorical(df["industry_group"], categories=industry_levels)

    pro_levels = sorted(df["ballroom_partner"].dropna().unique().tolist())
    df["pro_code"] = pd.Categorical(df["ballroom_partner"], categories=pro_levels).codes

    season_levels = sorted(df["season"].dropna().unique().tolist())
    df["season_code"] = pd.Categorical(df["season"], categories=season_levels).codes

    columns = []
    terms = []
    term_map = {}

    # age
    columns.append(df["celebrity_age_during_season"].values)
    terms.append(s(len(columns) - 1, n_splines=12))
    term_map["age"] = len(terms) - 1

    # week
    if include_week:
        columns.append(df["week_index"].values)
        terms.append(s(len(columns) - 1, n_splines=8))
        term_map["week"] = len(terms) - 1

    # trend/cum
    if include_trend:
        columns.append(df["trend_z"].values)
        terms.append(l(len(columns) - 1))
        term_map["trend_z"] = len(terms) - 1
    if include_cum:
        columns.append(df["cum_z"].values)
        terms.append(l(len(columns) - 1))
        term_map["cum_z"] = len(terms) - 1

    # industry
    columns.append(df["industry_group_use"].cat.codes.values)
    terms.append(f(len(columns) - 1))
    term_map["industry"] = len(terms) - 1

    # region
    columns.append(df["is_us"].values)
    terms.append(f(len(columns) - 1))
    term_map["is_us"] = len(terms) - 1

    # pro
    columns.append(df["pro_code"].values)
    terms.append(f(len(columns) - 1))
    term_map["pro"] = len(terms) - 1

    # season
    columns.append(df["season_code"].values)
    terms.append(f(len(columns) - 1))
    term_map["season"] = len(terms) - 1

    # judge_z (fan model)
    if include_judge:
        columns.append(df["judge_z"].values)
        terms.append(l(len(columns) - 1))
        term_map["judge_z"] = len(terms) - 1

    X = np.column_stack(columns)

    meta = {
        "industry_levels": industry_levels,
    }
    return X, terms, term_map, meta


def extract_linear_coef(gam, term_idx):
    idx = gam.terms.get_coef_indices(term_idx)
    return float(gam.coef_[idx][0])


def extract_factor_effects(gam, term_idx, levels):
    idx = gam.terms.get_coef_indices(term_idx)
    coefs = gam.coef_[idx]
    return {level: float(coefs[i]) for i, level in enumerate(levels)}


def extract_effect_vector(gam, term_map, meta):
    effects = {}
    if "trend_z" in term_map:
        effects["trend_z"] = extract_linear_coef(gam, term_map["trend_z"])
    if "cum_z" in term_map:
        effects["cum_z"] = extract_linear_coef(gam, term_map["cum_z"])
    if "industry" in term_map:
        ind = extract_factor_effects(gam, term_map["industry"], meta["industry_levels"])
        for level, val in ind.items():
            if level != "Other":
                effects[f"Industry: {level}"] = val
    if "is_us" in term_map:
        reg = extract_factor_effects(gam, term_map["is_us"], ["non-US", "US"])
        effects["US (vs non-US)"] = reg["US"]
    if "judge_z" in term_map:
        effects["judge_z"] = extract_linear_coef(gam, term_map["judge_z"])
    return effects


def combine_terms(terms):
    if not terms:
        raise ValueError("empty terms")
    out = terms[0]
    for term in terms[1:]:
        out = out + term
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weekly-path",
        default="data/processed/task3_weekly_model.csv",
        help="Weekly modeling table.",
    )
    parser.add_argument(
        "--out-summary",
        default="data/processed/task3_sensitivity_summary.csv",
        help="Sensitivity results table.",
    )
    parser.add_argument(
        "--tag",
        default="",
        help="Optional tag for output filenames (e.g., v3).",
    )
    parser.add_argument(
        "--fig-dir",
        default="figures",
        help="Directory for figures.",
    )
    args = parser.parse_args()
    tag = args.tag.strip()

    df = pd.read_csv(args.weekly_path)
    judge_df = df[df["judge_total"].notna()].copy()
    fan_df = df[df["fan_share_mean"].notna()].copy()

    variants = [
        {"name": "base", "include_week": True, "include_trend": True, "include_cum": True, "include_judge": True, "use_alt_industry": False},
        {"name": "no_week", "include_week": False, "include_trend": True, "include_cum": True, "include_judge": True, "use_alt_industry": False},
        {"name": "no_trend_cum", "include_week": True, "include_trend": False, "include_cum": False, "include_judge": True, "use_alt_industry": False},
        {"name": "no_judge_in_fan", "include_week": True, "include_trend": True, "include_cum": True, "include_judge": False, "use_alt_industry": False},
        {"name": "alt_industry", "include_week": True, "include_trend": True, "include_cum": True, "include_judge": True, "use_alt_industry": True},
    ]

    rows = []
    for v in variants:
        X_j, terms_j, map_j, meta_j = build_design(
            judge_df,
            use_alt_industry=v["use_alt_industry"],
            include_week=v["include_week"],
            include_trend=v["include_trend"],
            include_cum=v["include_cum"],
            include_judge=False,
        )
        y_j = judge_df["judge_z"].values
        gam_j = LinearGAM(combine_terms(terms_j)).gridsearch(X_j, y_j, lam=[0.1, 1, 10])

        X_f, terms_f, map_f, meta_f = build_design(
            fan_df,
            use_alt_industry=v["use_alt_industry"],
            include_week=v["include_week"],
            include_trend=v["include_trend"],
            include_cum=v["include_cum"],
            include_judge=v["include_judge"],
        )
        y_f = logit(fan_df["fan_share_mean"]).values
        gam_f = LinearGAM(combine_terms(terms_f)).gridsearch(X_f, y_f, lam=[0.1, 1, 10])

        eff_j = extract_effect_vector(gam_j, map_j, meta_j)
        eff_f = extract_effect_vector(gam_f, map_f, meta_f)
        common = sorted(set(eff_j.keys()) & set(eff_f.keys()))
        if not common:
            rows.append({"variant": v["name"], "sign_agreement": np.nan, "cosine_similarity": np.nan, "pearson_corr": np.nan, "mean_abs_gap": np.nan})
            continue
        j = np.array([eff_j[k] for k in common])
        f = np.array([eff_f[k] for k in common])
        sign_agree = float((np.sign(j) == np.sign(f)).mean())
        cosine = float((j @ f) / (np.linalg.norm(j) * np.linalg.norm(f)))
        pearson = float(pd.Series(j).corr(pd.Series(f)))
        mean_abs_gap = float(np.mean(np.abs(f - j)))
        rows.append(
            {
                "variant": v["name"],
                "sign_agreement": sign_agree,
                "cosine_similarity": cosine,
                "pearson_corr": pearson,
                "mean_abs_gap": mean_abs_gap,
            }
        )

    summary = pd.DataFrame(rows).set_index("variant")
    out_summary = Path(args.out_summary)
    if tag:
        out_summary = out_summary.with_name(f"{out_summary.stem}_{tag}{out_summary.suffix}")
    summary.to_csv(out_summary)

    # Heatmap
    palette_map = apply_task3_style()
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    std = (summary - summary.mean()) / summary.std(ddof=0)
    cmap = sns.diverging_palette(240, 10, as_cmap=True)
    sns.heatmap(
        std,
        cmap=cmap,
        center=0,
        annot=summary.round(2),
        fmt="",
        linewidths=0.5,
        cbar_kws={"label": "Standardized score"},
        ax=ax,
    )
    ax.set_title("Sensitivity: Judges vs Fans (GAM)")
    plt.tight_layout()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fig_dir = Path(args.fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_name = f"task3_sensitivity_heatmap_{tag}_{timestamp}.png" if tag else f"task3_sensitivity_heatmap_{timestamp}.png"
    fig_path = fig_dir / fig_name
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)

    print("Saved sensitivity summary:", out_summary)
    print("Figure:", fig_path)


if __name__ == "__main__":
    main()
