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


def tag_path(path_str: str, tag: str) -> Path:
    path = Path(path_str)
    if not tag:
        return path
    return path.with_name(f"{path.stem}_{tag}{path.suffix}")


def tag_figure(base: str, tag: str, timestamp: str) -> str:
    if tag:
        return f"{base}_{tag}_{timestamp}.png"
    return f"{base}_{timestamp}.png"


def build_design(df: pd.DataFrame):
    df = df.copy()
    df["trend_z"] = zscore(df["performance_trend"])
    df["cum_z"] = zscore(df["cumulative_score"])

    industry_levels = ["Other", "Actor", "Singer", "Athlete", "Reality-TV"]
    df["industry_group"] = pd.Categorical(df["industry_group"], categories=industry_levels)

    pro_levels = sorted(df["ballroom_partner"].dropna().unique().tolist())
    df["pro_code"] = pd.Categorical(df["ballroom_partner"], categories=pro_levels).codes

    season_levels = sorted(df["season"].dropna().unique().tolist())
    df["season_code"] = pd.Categorical(df["season"], categories=season_levels).codes

    X = np.column_stack(
        [
            df["celebrity_age_during_season"].values,  # 0 age
            df["week_index"].values,  # 1 week
            df["trend_z"].values,  # 2 trend
            df["cum_z"].values,  # 3 cumulative
            df["industry_group"].cat.codes.values,  # 4 industry
            df["is_us"].values,  # 5 is_us
            df["pro_code"].values,  # 6 pro
            df["season_code"].values,  # 7 season
        ]
    )

    meta = {
        "industry_levels": industry_levels,
        "pro_levels": pro_levels,
        "season_levels": season_levels,
        "trend_mean": df["trend_z"].mean(),
        "cum_mean": df["cum_z"].mean(),
        "age_median": df["celebrity_age_during_season"].median(),
        "week_median": df["week_index"].median(),
        "industry_mode": int(df["industry_group"].cat.codes.mode().iloc[0]),
        "is_us_mode": int(pd.Series(df["is_us"]).mode().iloc[0]),
        "pro_mode": int(pd.Series(df["pro_code"]).mode().iloc[0]),
        "season_mode": int(pd.Series(df["season_code"]).mode().iloc[0]),
    }
    return X, meta


def fit_gam(X, y, include_judge=False):
    terms = s(0, n_splines=12) + s(1, n_splines=8) + l(2) + l(3) + f(4) + f(5) + f(6) + f(7)
    if include_judge:
        terms = terms + l(8)
    gam = LinearGAM(terms)
    gam.gridsearch(X, y, lam=[0.1, 1, 10])
    return gam


def extract_linear_coef(gam, term_idx):
    idx = gam.terms.get_coef_indices(term_idx)
    return float(gam.coef_[idx][0])


def extract_factor_effects(gam, term_idx, levels):
    idx = gam.terms.get_coef_indices(term_idx)
    coefs = gam.coef_[idx]
    cov = gam.statistics_["cov"]
    se = np.sqrt(np.diag(cov))[idx]
    rows = []
    for code, label in enumerate(levels):
        effect = float(coefs[code])
        rows.append(
            {
                "level": label,
                "effect": effect,
                "ci_low": effect - 1.96 * se[code],
                "ci_high": effect + 1.96 * se[code],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weekly-path",
        default="data/processed/task3_weekly_model.csv",
        help="Weekly modeling table from step1.",
    )
    parser.add_argument(
        "--out-coef",
        default="data/processed/task3_model_coefficients.csv",
        help="Output merged coefficients table.",
    )
    parser.add_argument(
        "--out-fit",
        default="data/processed/task3_model_fit_stats.csv",
        help="Output fit statistics table.",
    )
    parser.add_argument(
        "--out-pro",
        default="data/processed/task3_pro_buff.csv",
        help="Output pro buff table.",
    )
    parser.add_argument(
        "--out-consistency",
        default="data/processed/task3_judge_fan_consistency.csv",
        help="Output judges vs fans coefficient consistency metrics.",
    )
    parser.add_argument(
        "--out-var",
        default="data/processed/task3_gam_variance_components.csv",
        help="Output variance share summary.",
    )
    parser.add_argument(
        "--out-smooth",
        default="data/processed/task3_smooth_effects.csv",
        help="Output smooth effects curves.",
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

    out_coef = tag_path(args.out_coef, tag)
    out_fit = tag_path(args.out_fit, tag)
    out_pro = tag_path(args.out_pro, tag)
    out_consistency = tag_path(args.out_consistency, tag)
    out_var = tag_path(args.out_var, tag)
    out_smooth = tag_path(args.out_smooth, tag)

    df = pd.read_csv(args.weekly_path)

    # Judges model
    judge_df = df[df["judge_total"].notna()].copy()
    X_judge, meta_judge = build_design(judge_df)
    y_judge = judge_df["judge_z"].values
    gam_judge = fit_gam(X_judge, y_judge, include_judge=False)

    # Fans model
    fan_df = df[df["fan_share_mean"].notna()].copy()
    X_fan, meta_fan = build_design(fan_df)
    fan_logit = logit(fan_df["fan_share_mean"]).values
    X_fan = np.column_stack([X_fan, fan_df["judge_z"].values])
    gam_fan = fit_gam(X_fan, fan_logit, include_judge=True)

    # Fit stats
    fit_stats = pd.DataFrame(
        [
            {"model": "judge", "nobs": len(y_judge), "aic": gam_judge.statistics_["AIC"], "pseudo_r2": gam_judge.statistics_["pseudo_r2"]},
            {"model": "fan", "nobs": len(fan_logit), "aic": gam_fan.statistics_["AIC"], "pseudo_r2": gam_fan.statistics_["pseudo_r2"]},
        ]
    )
    fit_stats.to_csv(out_fit, index=False)

    # Coefficients: linear and factor terms
    coef_rows = []
    # Linear terms (trend_z, cum_z)
    coef_rows.append({"term": "trend_z", "judge_coef": extract_linear_coef(gam_judge, 2)})
    coef_rows.append({"term": "cum_z", "judge_coef": extract_linear_coef(gam_judge, 3)})

    coef_rows.append({"term": "trend_z", "fan_coef": extract_linear_coef(gam_fan, 2)})
    coef_rows.append({"term": "cum_z", "fan_coef": extract_linear_coef(gam_fan, 3)})
    coef_rows.append({"term": "judge_z", "fan_coef": extract_linear_coef(gam_fan, 8)})

    # Industry factor effects
    judge_ind = extract_factor_effects(gam_judge, 4, meta_judge["industry_levels"])
    fan_ind = extract_factor_effects(gam_fan, 4, meta_fan["industry_levels"])

    for _, row in judge_ind.iterrows():
        if row["level"] != "Other":
            coef_rows.append({"term": f"Industry: {row['level']}", "judge_coef": row["effect"]})
    for _, row in fan_ind.iterrows():
        if row["level"] != "Other":
            coef_rows.append({"term": f"Industry: {row['level']}", "fan_coef": row["effect"]})

    # Region (is_us)
    judge_region = extract_factor_effects(gam_judge, 5, ["non-US", "US"])
    fan_region = extract_factor_effects(gam_fan, 5, ["non-US", "US"])
    coef_rows.append({"term": "US (vs non-US)", "judge_coef": float(judge_region.loc[judge_region["level"] == "US", "effect"].iloc[0])})
    coef_rows.append({"term": "US (vs non-US)", "fan_coef": float(fan_region.loc[fan_region["level"] == "US", "effect"].iloc[0])})

    coef = pd.DataFrame(coef_rows)
    coef = coef.groupby("term", as_index=False).agg({"judge_coef": "first", "fan_coef": "first"})
    coef.to_csv(out_coef, index=False)

    # Consistency metrics (linear + industry + region)
    common = coef.dropna(subset=["judge_coef", "fan_coef"])
    judge_vec = common["judge_coef"].values
    fan_vec = common["fan_coef"].values
    sign_agree = float((np.sign(judge_vec) == np.sign(fan_vec)).mean())
    cosine = float((judge_vec @ fan_vec) / (np.linalg.norm(judge_vec) * np.linalg.norm(fan_vec)))
    pearson = float(pd.Series(judge_vec).corr(pd.Series(fan_vec)))
    mean_abs_gap = float(np.mean(np.abs(fan_vec - judge_vec)))

    # Smooth effect correlations
    age_grid = np.linspace(
        np.percentile(judge_df["celebrity_age_during_season"], 5),
        np.percentile(judge_df["celebrity_age_during_season"], 95),
        80,
    )
    week_grid = np.arange(int(df["week_index"].min()), int(df["week_index"].max()) + 1)

    base_judge = np.array([
        meta_judge["age_median"],
        meta_judge["week_median"],
        meta_judge["trend_mean"],
        meta_judge["cum_mean"],
        meta_judge["industry_mode"],
        meta_judge["is_us_mode"],
        meta_judge["pro_mode"],
        meta_judge["season_mode"],
    ])
    base_fan = np.array([
        meta_fan["age_median"],
        meta_fan["week_median"],
        meta_fan["trend_mean"],
        meta_fan["cum_mean"],
        meta_fan["industry_mode"],
        meta_fan["is_us_mode"],
        meta_fan["pro_mode"],
        meta_fan["season_mode"],
        fan_df["judge_z"].mean(),
    ])

    X_age_j = np.tile(base_judge, (len(age_grid), 1))
    X_age_j[:, 0] = age_grid
    X_age_f = np.tile(base_fan, (len(age_grid), 1))
    X_age_f[:, 0] = age_grid

    age_j = gam_judge.partial_dependence(term=0, X=X_age_j)
    age_f = gam_fan.partial_dependence(term=0, X=X_age_f)
    age_f = 1 / (1 + np.exp(-age_f))

    X_week_j = np.tile(base_judge, (len(week_grid), 1))
    X_week_j[:, 1] = week_grid
    X_week_f = np.tile(base_fan, (len(week_grid), 1))
    X_week_f[:, 1] = week_grid

    week_j = gam_judge.partial_dependence(term=1, X=X_week_j)
    week_f = gam_fan.partial_dependence(term=1, X=X_week_f)
    week_f = 1 / (1 + np.exp(-week_f))

    age_corr = float(pd.Series(age_j).corr(pd.Series(age_f)))
    week_corr = float(pd.Series(week_j).corr(pd.Series(week_f)))

    consistency = pd.DataFrame(
        {
            "metric": [
                "sign_agreement",
                "cosine_similarity",
                "pearson_corr",
                "mean_abs_gap",
                "age_curve_corr",
                "week_curve_corr",
            ],
            "value": [sign_agree, cosine, pearson, mean_abs_gap, age_corr, week_corr],
        }
    )
    consistency.to_csv(out_consistency, index=False)

    # Pro buff (factor effects)
    pro_effects = extract_factor_effects(gam_judge, 6, meta_judge["pro_levels"])
    pro_effects = pro_effects.rename(columns={"level": "ballroom_partner", "effect": "pro_effect"})
    pro_effects.to_csv(out_pro, index=False)

    # Variance share: pro and season contribution
    pro_term = gam_judge.partial_dependence(term=6, X=X_judge)
    season_term = gam_judge.partial_dependence(term=7, X=X_judge)
    var_y = np.var(y_judge)
    var_pro = np.var(pro_term)
    var_season = np.var(season_term)
    var_df = pd.DataFrame(
        [
            {"metric": "pro_variance_share", "value": var_pro / var_y if var_y > 0 else np.nan},
            {"metric": "season_variance_share", "value": var_season / var_y if var_y > 0 else np.nan},
        ]
    )
    var_df.to_csv(out_var, index=False)

    # Smooth effects data
    smooth_df = pd.DataFrame(
        {
            "age": age_grid,
            "judge_age_effect": age_j,
            "fan_age_effect": age_f,
        }
    )
    smooth_week = pd.DataFrame(
        {
            "week": week_grid,
            "judge_week_effect": week_j,
            "fan_week_effect": week_f,
        }
    )
    smooth_out = pd.concat([smooth_df, smooth_week], axis=1)
    smooth_out.to_csv(out_smooth, index=False)

    # Plotting
    palette_map = apply_task3_style()
    palette = [palette_map["judge"], palette_map["fan"]]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fig_dir = Path(args.fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Dumbbell
    coef_common = coef.dropna(subset=["judge_coef", "fan_coef"]).copy()
    coef_common["gap"] = (coef_common["fan_coef"] - coef_common["judge_coef"]).abs()
    coef_common = coef_common.sort_values("gap", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(coef_common.shape[0])
    ax.hlines(y, coef_common["judge_coef"], coef_common["fan_coef"], color="lightgray", linewidth=2)
    ax.scatter(coef_common["judge_coef"], y, color=palette[0], s=70, label="Judges")
    ax.scatter(coef_common["fan_coef"], y, color=palette[1], s=70, label="Fans")
    ax.axvline(0, color=palette_map["muted"], linewidth=1, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(coef_common["term"])
    ax.set_xlabel("Coefficient (link scale)")
    ax.set_title("Feature Effects: Judges vs Fans (GAM)")
    ax.legend(frameon=False, loc="lower right")
    sns.despine(ax=ax, left=True, bottom=True)
    plt.tight_layout()
    dumbbell_path = fig_dir / tag_figure("task3_coef_dumbbell", tag, timestamp)
    fig.savefig(dumbbell_path, dpi=300)
    plt.close(fig)

    # Heatmap
    heat_df = coef_common.set_index("term")[["judge_coef", "fan_coef"]]
    fig, ax = plt.subplots(figsize=(7, 5.6))
    cmap = sns.diverging_palette(240, 10, as_cmap=True)
    sns.heatmap(
        heat_df,
        cmap=cmap,
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"label": "Coefficient"},
        ax=ax,
    )
    ax.set_title("Coefficient Heatmap: Judges vs Fans (GAM)")
    plt.tight_layout()
    heat_path = fig_dir / tag_figure("task3_coef_heatmap", tag, timestamp)
    fig.savefig(heat_path, dpi=300)
    plt.close(fig)

    # Gap bar
    gap_df = coef_common.copy()
    gap_df["diff"] = gap_df["fan_coef"] - gap_df["judge_coef"]
    gap_df = gap_df.sort_values("diff")
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [palette_map["fan"] if v > 0 else palette_map["judge"] for v in gap_df["diff"]]
    ax.barh(gap_df["term"], gap_df["diff"], color=colors, alpha=0.9)
    ax.axvline(0, color=palette_map["muted"], linewidth=1, linestyle="--")
    ax.set_xlabel("Fan coef - Judge coef")
    ax.set_title("Effect Gap by Feature (GAM)")
    sns.despine(ax=ax, left=True, bottom=True)
    plt.tight_layout()
    gap_path = fig_dir / tag_figure("task3_coef_gap", tag, timestamp)
    fig.savefig(gap_path, dpi=300)
    plt.close(fig)

    # Pro buff caterpillar (Enhanced for MCM)
    top_n = 10
    pro_sorted = pro_effects.sort_values("pro_effect", ascending=False)
    cat_df = pd.concat([pro_sorted.head(top_n), pro_sorted.tail(top_n)]).sort_values("pro_effect")
    
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    
    # 1. Color mapping: positive effects in blue, negative in red
    colors = [palette_map["judge"] if x > 0 else "#D65151" for x in cat_df["pro_effect"]]
    
    # 2. Draw horizontal background lines for visual guidance
    ax.hlines(
        np.arange(cat_df.shape[0]),
        xmin=cat_df["ci_low"],
        xmax=cat_df["ci_high"],
        color=palette_map["muted"],
        alpha=0.2,
        linewidth=1,
        zorder=1
    )
    
    # 3. Draw error bars (Confidence Intervals) - individually for each point
    for i, (idx, row) in enumerate(cat_df.iterrows()):
        ax.errorbar(
            row["pro_effect"],
            i,
            xerr=[[row["pro_effect"] - row["ci_low"]], [row["ci_high"] - row["pro_effect"]]],
            fmt='none',
            ecolor=colors[i],
            elinewidth=2.5,
            capsize=4,
            capthick=1.5,
            alpha=0.6,
            zorder=2
        )
    
    # 4. Draw center points (Effect Size) with white edge for prominence
    ax.scatter(
        cat_df["pro_effect"],
        np.arange(cat_df.shape[0]),
        c=colors,
        s=100,
        edgecolor="white",
        linewidth=1.2,
        zorder=3
    )
    
    # 5. Emphasize zero line
    ax.axvline(0, color=palette_map["muted"], linewidth=1.5, linestyle="--", alpha=0.8)
    
    # 6. Axis beautification
    ax.set_yticks(np.arange(cat_df.shape[0]))
    ax.set_yticklabels(cat_df["ballroom_partner"], fontsize=11)
    
    # Remove y-axis grid, keep only x-axis grid
    ax.grid(True, axis='x', linestyle=':', alpha=0.6)
    ax.grid(False, axis='y')
    
    ax.set_xlabel("Relative Pro Effect Size (95% CI)", fontsize=12, fontweight='bold')
    ax.set_title("Pro Buff Ranking: Top & Bottom 10 Professional Dancers", 
                 fontsize=14, pad=20, fontweight='bold', loc='left')
    
    sns.despine(left=True, bottom=False)
    plt.tight_layout()
    pro_path = fig_dir / tag_figure("task3_pro_buff_caterpillar", tag, timestamp)
    fig.savefig(pro_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

    # Smooth effects plot
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    ax = axes[0]
    ax2 = ax.twinx()
    line1, = ax.plot(age_grid, age_j, color=palette_map["judge"], linewidth=2.2, label="Judges score (z)")
    line2, = ax2.plot(age_grid, age_f, color=palette_map["fan"], linewidth=2.2, label="Fan share")
    ax.set_xlabel("Age")
    ax.set_ylabel("Judge score (z)")
    ax2.set_ylabel("Fan share")
    ax.set_title("Age Effect (GAM)")
    ax2.grid(False)

    ax = axes[1]
    ax2 = ax.twinx()
    ax.plot(week_grid, week_j, color=palette_map["judge"], linewidth=2.2)
    ax2.plot(week_grid, week_f, color=palette_map["fan"], linewidth=2.2)
    ax.set_xlabel("Week")
    ax.set_ylabel("Judge score (z)")
    ax2.set_ylabel("Fan share")
    ax.set_title("Week Effect (GAM)")
    ax2.grid(False)

    fig.legend([line1, line2], ["Judges score (z)", "Fan share"], loc="lower center", ncol=2, frameon=False)
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    smooth_path = fig_dir / tag_figure("task3_smooth_effects", tag, timestamp)
    fig.savefig(smooth_path, dpi=300)
    plt.close(fig)

    print("Saved coefficients:", out_coef)
    print("Saved fit stats:", out_fit)
    print("Saved pro buff:", out_pro)
    print("Saved consistency:", out_consistency)
    print("Saved variance share:", out_var)
    print("Saved smooth effects data:", out_smooth)
    print("Figure:", dumbbell_path)
    print("Figure:", heat_path)
    print("Figure:", gap_path)
    print("Figure:", pro_path)
    print("Figure:", smooth_path)


if __name__ == "__main__":
    main()
