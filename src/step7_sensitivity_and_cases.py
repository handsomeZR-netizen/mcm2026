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


def main():
    parser = argparse.ArgumentParser(description='Sensitivity analysis + controversy plots')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--posterior', default='data/processed/abc_weekly_posterior.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--fig-dir', default='figures')
    parser.add_argument('--log-dir', default='outputs/sensitivity')
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
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
        handlers=[logging.FileHandler(log_dir / f'sensitivity_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    # --- Sensitivity: Rank vs Percent ---
    truth_eval = truth[truth['has_elim']].copy()
    if 'rule_period' not in truth_eval.columns:
        rule_periods = weekly[['season', 'week', 'rule_period']].drop_duplicates()
        truth_eval = truth_eval.merge(rule_periods, on=['season', 'week'], how='left')

    rows = []
    skipped = 0
    for _, t in truth_eval.iterrows():
        season = int(t['season'])
        week = int(t['week'])
        true_set = parse_name_set(t['elim_names'])

        df_week = weekly[(weekly['season'] == season) & (weekly['week'] == week)].copy()
        post_week = posterior[(posterior['season'] == season) & (posterior['week'] == week)].copy()
        if df_week.empty or post_week.empty:
            skipped += 1
            continue

        df_week = df_week.set_index('celebrity_name')
        post_week = post_week.set_index('celebrity_name')
        common = df_week.index.intersection(post_week.index)
        df_week = df_week.loc[common].copy()
        post_week = post_week.loc[common].copy()

        fan_votes = post_week['posterior_mean'].values
        judges_save = t['rule_period'] == 'bottom_two'

        # Rank rule
        out_rank = apply_rule(df_week.reset_index(), fan_votes, rule='rank', judges_save=judges_save)
        if judges_save:
            hit_rank = bool(set(out_rank['bottom_two']) & true_set)
        else:
            hit_rank = out_rank['eliminated'] in true_set

        # Percent rule
        out_pct = apply_rule(df_week.reset_index(), fan_votes, rule='percent', judges_save=judges_save)
        if judges_save:
            hit_pct = bool(set(out_pct['bottom_two']) & true_set)
        else:
            hit_pct = out_pct['eliminated'] in true_set

        rows.append({
            'season': season,
            'week': week,
            'judges_save': bool(judges_save),
            'hit_rank': hit_rank,
            'hit_percent': hit_pct,
        })

    sens_week = pd.DataFrame(rows)
    sens_week_path = out_dir / 'sensitivity_weekly.csv'
    sens_week.to_csv(sens_week_path, index=False)

    sens_season = (
        sens_week.groupby('season', as_index=False)
        .agg(
            consistency_rank=('hit_rank', 'mean'),
            consistency_percent=('hit_percent', 'mean'),
            weeks=('week', 'count')
        )
    )
    sens_season['season'] = pd.to_numeric(sens_season['season'], errors='coerce')
    sens_season['delta_rank_minus_percent'] = sens_season['consistency_rank'] - sens_season['consistency_percent']
    sens_season_path = out_dir / 'sensitivity_season.csv'
    sens_season.to_csv(sens_season_path, index=False)

    # --- Controversy cases ---
    controversy = ['Jerry Rice', 'Billy Ray Cyrus', 'Bristol Palin', 'Bobby Bones']
    case = posterior[posterior['celebrity_name'].isin(controversy)].copy()
    case = case.merge(
        weekly[['season', 'week', 'celebrity_name', 'judge_total']],
        on=['season', 'week', 'celebrity_name'],
        how='left'
    )
    case['week'] = pd.to_numeric(case['week'], errors='coerce')
    case_path = out_dir / 'controversy_posterior_weeks.csv'
    case.to_csv(case_path, index=False)

    # Plot settings
    sns.set_theme(style='whitegrid')
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.labelsize'] = 11

    # Plot A: Consistency Rank vs Percent by Season
    sens_long = sens_season.melt(
        id_vars=['season'],
        value_vars=['consistency_rank', 'consistency_percent'],
        var_name='rule', value_name='consistency'
    )
    sens_long['season'] = pd.to_numeric(sens_long['season'], errors='coerce')
    sens_long = sens_long.dropna(subset=['season'])
    sens_long['season_num'] = sens_long['season'].astype(float)
    sens_long['rule'] = sens_long['rule'].replace({
        'consistency_rank': 'Rank',
        'consistency_percent': 'Percent',
    })

    fig1, ax1 = plt.subplots(figsize=(10, 4.5))
    palette = sns.color_palette('crest', n_colors=2)
    sns.lineplot(
        data=sens_long,
        x='season_num', y='consistency', hue='rule',
        palette=palette, linewidth=2.2, ax=ax1
    )
    ax1.set_title('Consistency by Season: Rank vs Percent')
    ax1.set_xlabel('Season')
    ax1.set_ylabel('Consistency Rate')
    ax1.set_ylim(0, 1)
    ax1.tick_params(axis='x', rotation=90)
    sns.despine(ax=ax1)
    fig1.tight_layout()
    fig1_path = fig_dir / f'sensitivity_rank_vs_percent_{run_ts}.png'
    fig1.savefig(fig1_path, dpi=300)

    # Plot B: Delta (Rank - Percent)
    fig2, ax2 = plt.subplots(figsize=(10, 4.2))
    sens_season = sens_season.dropna(subset=['season'])
    sens_season['season_num'] = sens_season['season'].astype(float)
    sns.barplot(
        data=sens_season,
        x='season_num', y='delta_rank_minus_percent', hue='season_num',
        palette=sns.color_palette('mako', n_colors=len(sens_season)),
        ax=ax2, legend=False
    )
    ax2.axhline(0, color='#666666', linewidth=1, linestyle='--')
    ax2.set_title('Consistency Difference: Rank minus Percent')
    ax2.set_xlabel('Season')
    ax2.set_ylabel('Consistency Difference')
    ax2.tick_params(axis='x', rotation=90)
    sns.despine(ax=ax2)
    fig2.tight_layout()
    fig2_path = fig_dir / f'sensitivity_delta_{run_ts}.png'
    fig2.savefig(fig2_path, dpi=300)

    # Plot C: Violin distribution of posterior means across weeks (controversy)
    fig3, ax3 = plt.subplots(figsize=(7.5, 4.8))
    pal = sns.color_palette('crest', n_colors=len(controversy))
    sns.violinplot(
        data=case, y='celebrity_name', x='posterior_mean', hue='celebrity_name',
        palette=pal, inner='quart', cut=0, linewidth=1, ax=ax3, legend=False
    )
    sns.stripplot(
        data=case, y='celebrity_name', x='posterior_mean',
        color='0.25', size=2.5, alpha=0.45, ax=ax3
    )
    ax3.set_title('Posterior Vote Share Distribution (Controversial Contestants)')
    ax3.set_xlabel('Posterior Vote Share (Mean)')
    ax3.set_ylabel('Contestant')
    sns.despine(ax=ax3)
    fig3.tight_layout()
    fig3_path = fig_dir / f'controversy_violin_{run_ts}.png'
    fig3.savefig(fig3_path, dpi=300)

    # Plot D: Faceted time series of posterior mean by week
    g = sns.FacetGrid(
        case, row='celebrity_name', hue='celebrity_name',
        aspect=3.5, height=1.2, palette=pal, sharey=False
    )
    g.map_dataframe(sns.lineplot, x='week', y='posterior_mean', linewidth=2)
    g.map_dataframe(sns.scatterplot, x='week', y='posterior_mean', s=18, alpha=0.6)
    g.set_axis_labels('Week', 'Posterior Mean')
    g.set_titles(row_template='{row_name}')
    g.figure.subplots_adjust(hspace=0.35)
    g.fig.suptitle('Posterior Vote Share by Week (Controversial Contestants)', y=1.02, fontsize=12)
    for ax in g.axes.flatten():
        sns.despine(ax=ax)
    fig4_path = fig_dir / f'controversy_timeseries_{run_ts}.png'
    g.savefig(fig4_path, dpi=300)

    summary = {
        'run_timestamp': run_ts,
        'sensitivity_weekly': str(sens_week_path),
        'sensitivity_season': str(sens_season_path),
        'controversy_data': str(case_path),
        'plots': [str(fig1_path), str(fig2_path), str(fig3_path), str(fig4_path)],
        'weeks_skipped': int(skipped),
    }
    summary_path = log_dir / f'sensitivity_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Sensitivity & Controversy Report',
        f'- run_timestamp: {run_ts}',
        f'- weeks_skipped: {skipped}',
        '## Outputs',
        f'- {sens_week_path}',
        f'- {sens_season_path}',
        f'- {case_path}',
        '## Figures',
        f'- {fig1_path}',
        f'- {fig2_path}',
        f'- {fig3_path}',
        f'- {fig4_path}',
    ]
    report_path = log_dir / f'sensitivity_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
