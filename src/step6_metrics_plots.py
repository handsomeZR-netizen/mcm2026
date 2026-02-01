import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from dwts_rules import apply_rule


def parse_name_set(names: str):
    if pd.isna(names):
        return set()
    parts = [p.strip() for p in str(names).split(' | ')]
    return {p for p in parts if p}


def compute_certainty_metrics(posterior: pd.DataFrame) -> pd.Series:
    p = posterior['posterior_mean'].values.astype(float)
    p = np.clip(p, 1e-12, None)
    p = p / p.sum() if p.sum() > 0 else p
    sd = posterior['posterior_sd'].values.astype(float)
    mean_sd = float(np.mean(sd)) if len(sd) else np.nan
    # normalized entropy
    entropy = -np.sum(p * np.log(p))
    entropy_norm = entropy / np.log(len(p)) if len(p) > 1 else 0.0
    return pd.Series({
        'certainty_inv_mean_sd': 1.0 / mean_sd if mean_sd > 0 else np.nan,
        'certainty_entropy': 1.0 - entropy_norm,
        'mean_sd': mean_sd,
    })


def main():
    parser = argparse.ArgumentParser(description='Compute consistency/certainty and plot')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--summary', default='data/processed/abc_weekly_summary.csv')
    parser.add_argument('--posterior', default='data/processed/abc_weekly_posterior.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--fig-dir', default='figures')
    parser.add_argument('--log-dir', default='outputs/metrics')
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    summary = pd.read_csv(args.summary)
    posterior = pd.read_csv(args.posterior)

    out_dir = Path(args.out_dir)
    fig_dir = Path(args.fig_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_dir / f'metrics_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    # Only evaluate weeks with elimination events
    truth_eval = truth[truth['has_elim']].copy()

    # Build predictions
    rows = []
    missing_weeks = 0

    for _, t in truth_eval.iterrows():
        season = int(t['season'])
        week = int(t['week'])
        true_set = parse_name_set(t['elim_names'])

        df_week = weekly[(weekly['season'] == season) & (weekly['week'] == week)].copy()
        if df_week.empty:
            missing_weeks += 1
            continue

        post_week = posterior[(posterior['season'] == season) & (posterior['week'] == week)].copy()
        if post_week.empty:
            missing_weeks += 1
            continue

        df_week = df_week.set_index('celebrity_name')
        post_week = post_week.set_index('celebrity_name')
        common = df_week.index.intersection(post_week.index)
        df_week = df_week.loc[common].copy()
        post_week = post_week.loc[common].copy()

        rule_info = summary[(summary['season'] == season) & (summary['week'] == week)]
        if rule_info.empty:
            rule_used = df_week['rule_period'].iloc[0] if 'rule_period' in df_week.columns else 'percent'
            judges_save = bool(rule_used == 'bottom_two')
            if rule_used == 'bottom_two':
                rule_used = 'rank'
        else:
            rule_used = rule_info['rule_used'].iloc[0]
            judges_save = bool(rule_info['judges_save'].iloc[0])

        fan_votes = post_week['posterior_mean'].values
        out = apply_rule(df_week.reset_index(), fan_votes, rule=rule_used, judges_save=judges_save)

        if judges_save:
            predicted_set = set(out['bottom_two'])
            hit = bool(predicted_set & true_set)
            predicted = ' | '.join(out['bottom_two'])
        else:
            predicted = out['eliminated']
            hit = predicted in true_set

        certainty = compute_certainty_metrics(post_week)

        rows.append({
            'season': season,
            'week': week,
            'rule_used': rule_used,
            'judges_save': judges_save,
            'true_elim': t['elim_names'],
            'predicted': predicted,
            'hit': hit,
            'acceptance_rate': float(rule_info['acceptance_rate'].iloc[0]) if not rule_info.empty else np.nan,
            **certainty.to_dict(),
        })

    metrics = pd.DataFrame(rows)
    metrics_path = out_dir / 'consistency_metrics.csv'
    metrics.to_csv(metrics_path, index=False)

    # Aggregate by season
    season_summary = (
        metrics.groupby('season', as_index=False)
        .agg(
            consistency_rate=('hit', 'mean'),
            acceptance_rate=('acceptance_rate', 'mean'),
            certainty_inv_mean_sd=('certainty_inv_mean_sd', 'mean'),
            certainty_entropy=('certainty_entropy', 'mean'),
        )
    )
    season_summary_path = out_dir / 'consistency_season_summary.csv'
    season_summary.to_csv(season_summary_path, index=False)

    # Plot style (soft gradients, academic)
    sns.set_theme(style='whitegrid')
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 11

    # Ensure numeric season for plotting
    season_summary['season'] = pd.to_numeric(season_summary['season'], errors='coerce').astype('Int64')

    # Plot 1: Consistency by season
    fig1, ax1 = plt.subplots(figsize=(10, 4.5))
    palette = sns.color_palette('crest', n_colors=len(season_summary))
    sns.barplot(
        data=season_summary,
        x='season', y='consistency_rate', hue='season',
        palette=palette, ax=ax1, legend=False
    )
    ax1.set_title('Consistency Rate by Season')
    ax1.set_xlabel('Season')
    ax1.set_ylabel('Consistency Rate')
    ax1.set_ylim(0, 1)
    ax1.tick_params(axis='x', rotation=90)
    sns.despine(ax=ax1)
    fig1.tight_layout()
    fig1_path = fig_dir / f'consistency_by_season_{run_ts}.png'
    fig1.savefig(fig1_path, dpi=300)

    # Plot 2: Certainty across weeks (median + IQR)
    week_summary = metrics.groupby('week').agg(
        median_certainty=('certainty_inv_mean_sd', 'median'),
        q25=('certainty_inv_mean_sd', lambda x: np.nanpercentile(x, 25)),
        q75=('certainty_inv_mean_sd', lambda x: np.nanpercentile(x, 75)),
    ).reset_index()
    week_summary['week'] = pd.to_numeric(week_summary['week'], errors='coerce')

    fig2, ax2 = plt.subplots(figsize=(7.5, 4.5))
    sns.lineplot(data=week_summary, x='week', y='median_certainty', color='#2a788e', linewidth=2.2, ax=ax2)
    ax2.fill_between(week_summary['week'], week_summary['q25'], week_summary['q75'], color='#8ecae6', alpha=0.35)
    ax2.set_title('Certainty by Week (Median with IQR)')
    ax2.set_xlabel('Week')
    ax2.set_ylabel('Certainty (1 / mean SD)')
    sns.despine(ax=ax2)
    fig2.tight_layout()
    fig2_path = fig_dir / f'certainty_by_week_{run_ts}.png'
    fig2.savefig(fig2_path, dpi=300)

    # Plot 3: Acceptance rate distribution
    fig3, ax3 = plt.subplots(figsize=(7.5, 4.5))
    sns.histplot(
        metrics['acceptance_rate'].dropna(),
        bins=20, kde=True, color='#5f6c7b', ax=ax3
    )
    ax3.set_title('Acceptance Rate Distribution')
    ax3.set_xlabel('Acceptance Rate')
    ax3.set_ylabel('Count')
    sns.despine(ax=ax3)
    fig3.tight_layout()
    fig3_path = fig_dir / f'acceptance_rate_dist_{run_ts}.png'
    fig3.savefig(fig3_path, dpi=300)

    # Report
    summary = {
        'run_timestamp': run_ts,
        'metrics_output': str(metrics_path),
        'season_summary_output': str(season_summary_path),
        'plots': [str(fig1_path), str(fig2_path), str(fig3_path)],
        'missing_weeks': int(missing_weeks),
        'weeks_evaluated': int(len(metrics)),
    }
    summary_path = log_dir / f'metrics_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Metrics & Plots Report',
        f'- run_timestamp: {run_ts}',
        f'- metrics_output: {metrics_path}',
        f'- season_summary_output: {season_summary_path}',
        f'- weeks_evaluated: {len(metrics)}',
        f'- missing_weeks: {missing_weeks}',
        '## Figures',
        f'- {fig1_path}',
        f'- {fig2_path}',
        f'- {fig3_path}',
    ]
    report_path = log_dir / f'metrics_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
