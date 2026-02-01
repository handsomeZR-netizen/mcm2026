import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def build_static_priors(base_df: pd.DataFrame) -> pd.DataFrame:
    """Build season-specific static priors using historical seasons only."""
    seasons = sorted(base_df['season'].dropna().unique())
    records = []

    for season in seasons:
        hist = base_df[base_df['season'] < season].copy()
        current = base_df[base_df['season'] == season].copy()

        overall_mean = hist['placement'].mean()
        overall_std = hist['placement'].std(ddof=0)
        if pd.isna(overall_mean):
            overall_mean = base_df['placement'].mean()
        if pd.isna(overall_std) or overall_std == 0:
            overall_std = base_df['placement'].std(ddof=0)
        if pd.isna(overall_std) or overall_std == 0:
            overall_std = 1.0

        # Industry stats
        industry_stats = (
            hist.groupby('celebrity_industry')['placement']
            .agg(['mean', 'count'])
            .rename(columns={'mean': 'industry_mean', 'count': 'industry_n'})
        )

        # Age regression
        hist_age = hist[['celebrity_age_during_season', 'placement']].dropna()
        age_n = len(hist_age)
        if age_n >= 10:
            slope, intercept = np.polyfit(hist_age['celebrity_age_during_season'], hist_age['placement'], 1)
        else:
            slope, intercept = 0.0, overall_mean

        for _, row in current.iterrows():
            industry = row['celebrity_industry']
            ind_mean = industry_stats.loc[industry, 'industry_mean'] if industry in industry_stats.index else overall_mean
            ind_n = int(industry_stats.loc[industry, 'industry_n']) if industry in industry_stats.index else 0
            industry_score = (overall_mean - ind_mean) / overall_std

            age = row['celebrity_age_during_season']
            if pd.isna(age):
                age_pred = overall_mean
                age_score = 0.0
            else:
                age_pred = intercept + slope * age
                age_score = (overall_mean - age_pred) / overall_std

            records.append({
                'season': int(season),
                'celebrity_name': row['celebrity_name'],
                'celebrity_industry': industry,
                'celebrity_age_during_season': row['celebrity_age_during_season'],
                'industry_mean_placement_hist': float(ind_mean),
                'industry_n_hist': int(ind_n),
                'industry_score': float(industry_score),
                'age_pred_placement_hist': float(age_pred) if not pd.isna(age_pred) else pd.NA,
                'age_score': float(age_score),
                'hist_n': int(len(hist)),
                'hist_age_n': int(age_n),
                'age_slope': float(slope),
                'age_intercept': float(intercept),
                'overall_mean_placement_hist': float(overall_mean),
                'overall_std_placement_hist': float(overall_std),
            })

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description='Build leakage-free priors for ABC')
    parser.add_argument('--input', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--log-dir', default='outputs/prior')
    parser.add_argument('--w-industry', type=float, default=1.0)
    parser.add_argument('--w-age', type=float, default=0.5)
    parser.add_argument('--w-trend', type=float, default=1.0)
    parser.add_argument('--trend-clip', type=float, default=2.0)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = log_dir / f'prior_{run_ts}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler()],
    )

    logging.info('Starting prior build')

    df = pd.read_csv(input_path)
    required = {
        'season', 'week', 'celebrity_name', 'celebrity_industry',
        'celebrity_age_during_season', 'placement', 'judge_total', 'active_in_week'
    }
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f'Missing required columns: {sorted(missing)}')

    # Static per-season priors
    base = (
        df[['season', 'celebrity_name', 'celebrity_industry', 'celebrity_age_during_season', 'placement']]
        .drop_duplicates(subset=['season', 'celebrity_name'])
        .copy()
    )
    static_priors = build_static_priors(base)
    static_path = out_dir / 'prior_static_by_season.csv'
    static_priors.to_csv(static_path, index=False)

    # Weekly trend features
    weekly = df[df['active_in_week']].copy()
    weekly = weekly.sort_values(['season', 'celebrity_name', 'week']).reset_index(drop=True)
    weekly['cum_sum'] = weekly.groupby(['season', 'celebrity_name'])['judge_total'].cumsum()
    weekly['cum_count'] = weekly.groupby(['season', 'celebrity_name']).cumcount() + 1
    weekly['prev_mean'] = (weekly['cum_sum'] - weekly['judge_total']) / (weekly['cum_count'] - 1)
    weekly.loc[weekly['cum_count'] == 1, 'prev_mean'] = np.nan
    weekly['trend'] = (weekly['judge_total'] - weekly['prev_mean']) / weekly['prev_mean']
    weekly.loc[weekly['prev_mean'].isna() | (weekly['prev_mean'] == 0), 'trend'] = 0.0
    weekly['trend_clipped'] = weekly['trend'].clip(-args.trend_clip, args.trend_clip)

    # Merge priors
    merged = weekly.merge(
        static_priors[['season', 'celebrity_name', 'industry_score', 'age_score']],
        on=['season', 'celebrity_name'],
        how='left',
    )
    merged['industry_score'] = merged['industry_score'].fillna(0.0)
    merged['age_score'] = merged['age_score'].fillna(0.0)

    # Alpha
    merged['alpha_raw'] = np.exp(
        args.w_industry * merged['industry_score'] +
        args.w_age * merged['age_score'] +
        args.w_trend * merged['trend_clipped']
    )
    merged['alpha_norm'] = merged.groupby(['season', 'week'])['alpha_raw'].transform(lambda x: x / x.sum())

    weekly_alpha = merged[[
        'season', 'week', 'celebrity_name', 'judge_total',
        'industry_score', 'age_score', 'trend', 'trend_clipped',
        'alpha_raw', 'alpha_norm'
    ]].copy()
    weekly_alpha_path = out_dir / 'prior_weekly_alpha.csv'
    weekly_alpha.to_csv(weekly_alpha_path, index=False)

    # Summary
    summary = {
        'run_timestamp': run_ts,
        'input': str(input_path),
        'static_output': str(static_path),
        'weekly_output': str(weekly_alpha_path),
        'w_industry': args.w_industry,
        'w_age': args.w_age,
        'w_trend': args.w_trend,
        'trend_clip': args.trend_clip,
        'n_static_rows': int(len(static_priors)),
        'n_weekly_rows': int(len(weekly_alpha)),
    }
    summary_path = log_dir / f'prior_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Prior Build Report',
        f'- run_timestamp: {run_ts}',
        f'- input: {input_path}',
        f'- static_output: {static_path}',
        f'- weekly_output: {weekly_alpha_path}',
        f'- w_industry: {args.w_industry}',
        f'- w_age: {args.w_age}',
        f'- w_trend: {args.w_trend}',
        f'- trend_clip: {args.trend_clip}',
        f'- n_static_rows: {len(static_priors)}',
        f'- n_weekly_rows: {len(weekly_alpha)}',
    ]
    report_path = log_dir / f'prior_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Prior build complete')
    logging.info('Report: %s', report_path)
    logging.info('Summary: %s', summary_path)


if __name__ == '__main__':
    main()
