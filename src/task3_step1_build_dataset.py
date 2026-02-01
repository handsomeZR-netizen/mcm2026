import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def map_industry(raw: str) -> str:
    if pd.isna(raw):
        return "Other"
    val = str(raw).strip().lower()
    if any(k in val for k in ["actor", "actress", "comedian", "producer"]):
        return "Actor"
    if any(k in val for k in ["singer", "musician", "rapper"]):
        return "Singer"
    if any(k in val for k in ["athlete", "racing", "sports"]):
        return "Athlete"
    if any(
        k in val
        for k in [
            "tv personality",
            "social media",
            "model",
            "beauty",
            "fashion",
            "fitness",
        ]
    ):
        return "Reality-TV"
    return "Other"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--long-path",
        default="data/processed/dwts_weekly_long.csv",
        help="Weekly long-form dataset from Task1.",
    )
    parser.add_argument(
        "--posterior-path",
        default="data/processed/abc_weekly_posterior.csv",
        help="Task1 posterior mean/sd by week.",
    )
    parser.add_argument(
        "--out-weekly",
        default="data/processed/task3_weekly_model.csv",
        help="Output weekly modeling table.",
    )
    parser.add_argument(
        "--out-survival",
        default="data/processed/task3_survival_base.csv",
        help="Output survival base table.",
    )
    parser.add_argument(
        "--out-summary",
        default="data/processed/task3_feature_summary.csv",
        help="Output feature summary table.",
    )
    args = parser.parse_args()

    long_df = pd.read_csv(args.long_path)
    posterior = pd.read_csv(args.posterior_path)

    # Keep only active contestants per week
    df = long_df[long_df["active_in_week"]].copy()

    # Standardize judge scores within each season-week
    week_stats = df.groupby(["season", "week"])["judge_total"]
    df["judge_mean_week"] = week_stats.transform("mean")
    df["judge_sd_week"] = week_stats.transform("std")
    df["judge_z"] = (df["judge_total"] - df["judge_mean_week"]) / df["judge_sd_week"]
    df["judge_z"] = df["judge_z"].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # Performance trend and cumulative score (within season-celebrity)
    df = df.sort_values(["season", "celebrity_name", "week"])
    df["performance_trend"] = (
        df.groupby(["season", "celebrity_name"])["judge_z"].diff().fillna(0.0)
    )
    df["cumulative_score"] = df.groupby(["season", "celebrity_name"])["judge_z"].expanding().mean().reset_index(level=[0, 1], drop=True)

    # Feature engineering
    df["industry_group"] = df["celebrity_industry"].map(map_industry)
    df["is_us"] = (df["celebrity_homecountry_region"] == "United States").astype(int)
    df["week_index"] = df["week"].astype(int)

    # Merge fan vote posterior
    posterior = posterior.rename(
        columns={
            "posterior_mean": "fan_share_mean",
            "posterior_sd": "fan_share_sd",
        }
    )
    df = df.merge(
        posterior[
            ["season", "week", "celebrity_name", "fan_share_mean", "fan_share_sd"]
        ],
        on=["season", "week", "celebrity_name"],
        how="left",
    )
    df["fan_share_available"] = (~df["fan_share_mean"].isna()).astype(int)

    # Save weekly modeling table
    Path(args.out_weekly).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_weekly, index=False)

    # Survival base table (one row per season-celebrity)
    base = (
        df.drop_duplicates(["season", "celebrity_name"])
        .loc[
            :,
            [
                "season",
                "celebrity_name",
                "ballroom_partner",
                "celebrity_industry",
                "industry_group",
                "celebrity_homecountry_region",
                "is_us",
                "celebrity_age_during_season",
                "results",
                "placement",
                "elim_week",
                "season_last_week",
            ],
        ]
        .copy()
    )
    base["event"] = base["results"].str.contains(
        "Eliminated|Withdrew|Disqualified|Withdrawn",
        case=False,
        na=False,
    ).astype(int)
    base["duration"] = base["elim_week"].astype(int)

    # Aggregate weekly signals
    agg = df.groupby(["season", "celebrity_name"]).agg(
        mean_judge_z=("judge_z", "mean"),
        mean_fan_share=("fan_share_mean", "mean"),
        mean_fan_sd=("fan_share_sd", "mean"),
        mean_trend=("performance_trend", "mean"),
        mean_cum_score=("cumulative_score", "mean"),
        weeks_observed=("week", "nunique"),
    )
    base = base.merge(agg, on=["season", "celebrity_name"], how="left")

    Path(args.out_survival).parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(args.out_survival, index=False)

    # Feature summary for reporting
    summary = (
        df.drop_duplicates(["season", "celebrity_name"])
        .groupby(["industry_group", "is_us"])
        .size()
        .reset_index(name="n_celebrities")
    )
    summary.to_csv(args.out_summary, index=False)

    print("Weekly modeling table:", args.out_weekly, "rows", df.shape[0])
    print("Survival base table:", args.out_survival, "rows", base.shape[0])
    print("Feature summary:", args.out_summary, "rows", summary.shape[0])
    print(
        "Fan share available ratio:",
        round(df["fan_share_available"].mean(), 3),
    )


if __name__ == "__main__":
    main()
