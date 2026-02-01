import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.duration.survfunc import SurvfuncRight

from task3_plot_style import apply_task3_style


def zscore(series: pd.Series) -> pd.Series:
    std = series.std(ddof=0)
    if std == 0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std

def tag_path(path_str: str, tag: str) -> Path:
    path = Path(path_str)
    if not tag:
        return path
    return path.with_name(f"{path.stem}_{tag}{path.suffix}")

def tag_figure(base: str, tag: str, timestamp: str) -> str:
    if tag:
        return f"{base}_{tag}_{timestamp}.png"
    return f"{base}_{timestamp}.png"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--survival-path",
        default="data/processed/task3_survival_base.csv",
        help="Survival base table from step1.",
    )
    parser.add_argument(
        "--pro-path",
        default="data/processed/task3_pro_buff.csv",
        help="Pro buff table from step2 (optional).",
    )
    parser.add_argument(
        "--out-cox",
        default="data/processed/task3_cox_summary.csv",
        help="Cox summary output.",
    )
    parser.add_argument(
        "--tag",
        default="",
        help="Optional tag for output filenames (e.g., v2).",
    )
    parser.add_argument(
        "--fig-dir",
        default="figures",
        help="Directory for figures.",
    )
    args = parser.parse_args()
    tag = args.tag.strip()
    out_cox = tag_path(args.out_cox, tag)

    surv = pd.read_csv(args.survival_path)

    # Merge pro buff if available
    pro_path = Path(args.pro_path)
    if pro_path.exists():
        pro_df = pd.read_csv(pro_path)
        surv = surv.merge(pro_df[["ballroom_partner", "pro_effect"]], on="ballroom_partner", how="left")
    else:
        surv["pro_effect"] = np.nan

    # Prepare features
    surv["age_z"] = zscore(surv["celebrity_age_during_season"])
    surv["age_z2"] = surv["age_z"] ** 2
    surv["judge_z_mean"] = zscore(surv["mean_judge_z"])
    surv["fan_share_mean_z"] = zscore(surv["mean_fan_share"])
    surv["pro_effect_z"] = zscore(surv["pro_effect"].fillna(0.0))

    industry_order = ["Other", "Actor", "Singer", "Athlete", "Reality-TV"]
    surv["industry_group"] = pd.Categorical(surv["industry_group"], categories=industry_order)

    surv = surv.dropna(subset=["duration", "event", "judge_z_mean", "fan_share_mean_z"])

    formula = (
        "duration ~ age_z + age_z2 + judge_z_mean + fan_share_mean_z + is_us + "
        "pro_effect_z + C(industry_group)"
    )
    model = PHReg.from_formula(formula, surv, status=surv["event"], ties="efron")
    res = model.fit()

    params = res.params
    se = res.bse
    pvals = res.pvalues
    terms = res.model.exog_names
    hr = np.exp(params)
    ci_low = np.exp(params - 1.96 * se)
    ci_high = np.exp(params + 1.96 * se)
    summary = pd.DataFrame(
        {
            "term": terms,
            "coef": params,
            "se": se,
            "p": pvals,
            "hazard_ratio": hr,
            "ci_low": ci_low,
            "ci_high": ci_high,
        }
    )
    summary.to_csv(out_cox, index=False)

    # Forest plot
    plot_df = summary[summary["term"] != "Intercept"].copy()
    label_map = {
        "age_z": "Age (z)",
        "age_z2": "Age^2",
        "judge_z_mean": "Mean judge score (z)",
        "fan_share_mean_z": "Mean fan share (z)",
        "is_us": "US (vs non-US)",
        "pro_effect_z": "Pro buff (z)",
        "C(industry_group)[T.Actor]": "Industry: Actor",
        "C(industry_group)[T.Singer]": "Industry: Singer",
        "C(industry_group)[T.Athlete]": "Industry: Athlete",
        "C(industry_group)[T.Reality-TV]": "Industry: Reality-TV",
    }
    plot_df["label"] = plot_df["term"].map(label_map).fillna(plot_df["term"])
    plot_df = plot_df.sort_values("hazard_ratio")

    palette_map = apply_task3_style()
    palette = sns.color_palette("crest", 1)
    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(plot_df.shape[0])
    ax.errorbar(
        plot_df["hazard_ratio"],
        y,
        xerr=[plot_df["hazard_ratio"] - plot_df["ci_low"], plot_df["ci_high"] - plot_df["hazard_ratio"]],
        fmt="o",
        color=palette[0],
        ecolor="#9aa0a6",
        elinewidth=2,
        capsize=3,
    )
    ax.axvline(1.0, color=palette_map["muted"], linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["label"])
    ax.set_xlabel("Hazard ratio (log scale)")
    ax.set_title("Cox Model: Elimination Hazard Ratios")
    ax.set_xscale("log")
    plt.tight_layout()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fig_dir = Path(args.fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_path = fig_dir / tag_figure("task3_cox_forest", tag, timestamp)
    fig.savefig(fig_path, dpi=300)
    plt.close(fig)

    # Kaplan-Meier curves by fan share tertile
    surv["fan_bucket"] = pd.qcut(
        surv["mean_fan_share"], q=3, labels=["Low fan share", "Mid fan share", "High fan share"]
    )
    fig, ax = plt.subplots(figsize=(7.8, 5.6))
    colors = [palette_map["judge"], palette_map["muted"], palette_map["fan"]]
    for bucket, color in zip(["Low fan share", "Mid fan share", "High fan share"], colors):
        sub = surv[surv["fan_bucket"] == bucket]
        if sub.empty:
            continue
        sf = SurvfuncRight(sub["duration"], sub["event"])
        ax.step(sf.surv_times, sf.surv_prob, where="post", label=bucket, color=color, linewidth=2)
    ax.set_xlabel("Week")
    ax.set_ylabel("Survival probability")
    ax.set_title("Kaplan-Meier Curves by Fan Share")
    ax.legend(frameon=False)
    sns.despine(ax=ax, left=True, bottom=True)
    plt.tight_layout()
    km_path = fig_dir / tag_figure("task3_km_fanshare", tag, timestamp)
    fig.savefig(km_path, dpi=300)
    plt.close(fig)

    print("Saved Cox summary:", out_cox)
    print("Figure:", fig_path)
    print("Figure:", km_path)


if __name__ == "__main__":
    main()
