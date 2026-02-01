import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description='Task2 Step3 postprocess: metrics + plots from dynamic sim')
    parser.add_argument('--sim-raw', default='data/processed/task2_dynamic_sim_raw.csv')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--frozen-metrics', default='data/processed/task2_metrics_rule_default.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--fig-dir', default='figures')
    parser.add_argument('--log-dir', default='outputs/task2')
    parser.add_argument('--focus-season', type=int, default=27)
    args = parser.parse_args()

    sim = pd.read_csv(args.sim_raw)
    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    frozen_metrics = pd.read_csv(args.frozen_metrics)

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
        handlers=[logging.FileHandler(log_dir / f'task2_step3_post_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    # Ensure numeric
    sim['is_hit'] = pd.to_numeric(sim['is_hit'], errors='coerce')
    sim['top3_safe'] = pd.to_numeric(sim['top3_safe'], errors='coerce')
    sim['is_fan_last'] = (sim['eliminated'] == sim['fan_last']).astype(int)

    metrics = (
        sim.groupby(['rule', 'strategy', 'judges_save'], as_index=False)
        .agg(
            sims=('season', 'size'),
            consistency=('is_hit', 'mean'),
            FII=('is_fan_last', 'mean'),
            TPI=('top3_safe', 'mean'),
        )
    )
    metrics_path = out_dir / 'task2_dynamic_metrics_rule_strategy.csv'
    metrics.to_csv(metrics_path, index=False)

    default_metrics = metrics[metrics['strategy'] == 'mix'].copy()
    default_metrics['cons_weighted'] = default_metrics['consistency'] * default_metrics['sims']
    default_metrics['FII_weighted'] = default_metrics['FII'] * default_metrics['sims']
    default_metrics['TPI_weighted'] = default_metrics['TPI'] * default_metrics['sims']

    default_metrics = (
        default_metrics.groupby('rule', as_index=False)
        .agg(
            sims=('sims', 'sum'),
            cons_weighted=('cons_weighted', 'sum'),
            FII_weighted=('FII_weighted', 'sum'),
            TPI_weighted=('TPI_weighted', 'sum')
        )
    )
    default_metrics['consistency'] = default_metrics['cons_weighted'] / default_metrics['sims']
    default_metrics['FII'] = default_metrics['FII_weighted'] / default_metrics['sims']
    default_metrics['TPI'] = default_metrics['TPI_weighted'] / default_metrics['sims']
    default_metrics = default_metrics[['rule', 'sims', 'consistency', 'FII', 'TPI']]

    default_path = out_dir / 'task2_dynamic_metrics_rule_default.csv'
    default_metrics.to_csv(default_path, index=False)

    # Elimination probability by week
    sim_counts = (
        sim.groupby(['rule', 'strategy', 'season', 'week']).size().rename('sim_n').reset_index()
    )
    elim_counts = (
        sim.groupby(['rule', 'strategy', 'season', 'week', 'eliminated']).size().rename('elim_n').reset_index()
    )
    elim_probs = elim_counts.merge(sim_counts, on=['rule', 'strategy', 'season', 'week'], how='left')
    elim_probs['elim_prob'] = elim_probs['elim_n'] / elim_probs['sim_n']
    elim_probs_path = out_dir / 'task2_dynamic_elim_prob_weekly.csv'
    elim_probs.to_csv(elim_probs_path, index=False)

    # Survival heatmap for focus season (mix policy)
    focus_season = args.focus_season
    active = weekly[
        (weekly['season'] == focus_season) & (weekly['active_in_week'])
    ][['season', 'week', 'celebrity_name', 'placement']].drop_duplicates()

    use_probs = elim_probs[elim_probs['strategy'] == 'mix'].copy()

    rules = ['rank', 'percent', 'adaptive_percent', 'official']
    survival_rows = []
    for rule in rules:
        rule_probs = use_probs[(use_probs['season'] == focus_season) & (use_probs['rule'] == rule)].copy()
        grid = active.copy()
        grid = grid.merge(
            rule_probs[['season', 'week', 'eliminated', 'elim_prob']],
            left_on=['season', 'week', 'celebrity_name'],
            right_on=['season', 'week', 'eliminated'],
            how='left'
        )
        grid['elim_prob'] = grid['elim_prob'].fillna(0.0)
        grid['survival_prob'] = 1.0 - grid['elim_prob']
        grid['rule'] = rule
        survival_rows.append(grid[['season', 'week', 'celebrity_name', 'placement', 'rule', 'survival_prob']])

    survival_df = pd.concat(survival_rows, ignore_index=True)
    survival_path = out_dir / 'task2_dynamic_survival_weekly_focus.csv'
    survival_df.to_csv(survival_path, index=False)

    # Plot settings
    sns.set_theme(style='whitegrid')
    rule_order = ['rank', 'percent', 'adaptive_percent', 'official']
    palette = sns.color_palette('crest', len(rule_order))
    rule_labels = {
        'rank': 'Rank',
        'percent': 'Percent',
        'adaptive_percent': 'Adaptive Percent',
        'official': 'Official',
    }
    rule_palette = {r: palette[i] for i, r in enumerate(rule_order)}
    rule_palette_labels = {rule_labels[r]: palette[i] for i, r in enumerate(rule_order)}

    # Plot A: Dynamic survival heatmap
    fig1, axes = plt.subplots(nrows=len(rule_order), ncols=1, figsize=(10, 7.5 + 1.6 * (len(rule_order) - 3)), sharex=True)
    for ax, rule in zip(axes, rule_order):
        df_rule = survival_df[survival_df['rule'] == rule].copy()
        if df_rule.empty:
            continue
        order = (
            df_rule[['celebrity_name', 'placement']]
            .drop_duplicates()
            .sort_values(by=['placement', 'celebrity_name'])
        )
        pivot = df_rule.pivot(index='celebrity_name', columns='week', values='survival_prob')
        pivot = pivot.reindex(order['celebrity_name'])
        sns.heatmap(
            pivot,
            cmap='crest',
            vmin=0,
            vmax=1,
            ax=ax,
            cbar=rule == rule_order[-1],
            cbar_kws={'label': 'Survival Probability'}
        )
        ax.set_title(f'Dynamic Survival (Season {focus_season}, Rule: {rule_labels[rule]})')
        ax.set_ylabel('Contestant')
    axes[-1].set_xlabel('Week')
    fig1.tight_layout()
    fig1_path = fig_dir / f'task2_dynamic_survival_heatmap_s{focus_season}_{run_ts}.png'
    fig1.savefig(fig1_path, dpi=300)

    # Plot B: Policy frontier (Frozen vs Dynamic)
    frozen = frozen_metrics.copy()
    frozen['scenario'] = 'Frozen'
    dynamic = default_metrics.copy()
    dynamic['scenario'] = 'Dynamic'
    compare = pd.concat([frozen, dynamic], ignore_index=True)
    compare['rule_label'] = compare['rule'].map(rule_labels)

    fig2, ax2 = plt.subplots(figsize=(6.8, 4.8))
    markers = {'Frozen': 'o', 'Dynamic': 's'}
    for _, row in compare.iterrows():
        ax2.scatter(
            row['FII'], row['TPI'],
            s=200 * row['consistency'],
            alpha=0.75,
            color=rule_palette.get(row['rule'], '#4c72b0'),
            marker=markers.get(row['scenario'], 'o'),
            edgecolor='white',
            linewidth=0.6,
        )
        ax2.text(row['FII'] + 0.005, row['TPI'] + 0.005, f"{row['rule_label']} ({row['scenario'][0]})", fontsize=8)

    from matplotlib.lines import Line2D
    rule_handles = [
        Line2D([0], [0], marker='o', color='w', label=rule_labels[r],
               markerfacecolor=rule_palette.get(r, '#4c72b0'), markersize=8)
        for r in rule_order
    ]
    scenario_handles = [
        Line2D([0], [0], marker=markers[s], color='w', label=s,
               markerfacecolor='gray', markersize=7)
        for s in markers
    ]

    ax2.set_xlabel('Fan Influence (FII)')
    ax2.set_ylabel('Technical Protection (TPI)')
    ax2.set_title('Policy Frontier: Frozen vs Dynamic')
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    legend1 = ax2.legend(handles=rule_handles, title='Rule', loc='lower left')
    ax2.add_artist(legend1)
    ax2.legend(handles=scenario_handles, title='Scenario', loc='upper right')
    fig2.tight_layout()
    fig2_path = fig_dir / f'task2_policy_frontier_{run_ts}.png'
    fig2.savefig(fig2_path, dpi=300)

    # Plot C: Dynamic consistency bar
    fig3, ax3 = plt.subplots(figsize=(6.2, 4.2))
    plot_df = default_metrics.copy()
    plot_df['rule_label'] = plot_df['rule'].map(rule_labels)
    sns.barplot(
        data=plot_df,
        x='rule_label',
        y='consistency',
        hue='rule_label',
        palette=rule_palette_labels,
        ax=ax3,
        legend=False
    )
    ax3.set_ylim(0, 1)
    ax3.set_title('Dynamic Consistency vs Reality')
    ax3.set_xlabel('Rule')
    ax3.set_ylabel('Consistency')
    fig3.tight_layout()
    fig3_path = fig_dir / f'task2_dynamic_consistency_bar_{run_ts}.png'
    fig3.savefig(fig3_path, dpi=300)

    # Plot D: Dynamic controversial cases (mix)
    cases = ['Jerry Rice', 'Billy Ray Cyrus', 'Bristol Palin', 'Bobby Bones']
    case_rows = []
    for rule in rules:
        rule_probs = use_probs[(use_probs['rule'] == rule) & (use_probs['eliminated'].isin(cases))].copy()
        rule_probs['survival_prob'] = 1.0 - rule_probs['elim_prob']
        rule_probs['rule_label'] = rule_probs['rule'].map(rule_labels)
        case_rows.append(rule_probs)

    case_df = pd.concat(case_rows, ignore_index=True)
    case_df = case_df.rename(columns={'eliminated': 'contestant'})

    g = sns.FacetGrid(
        case_df,
        row='contestant',
        hue='rule_label',
        height=1.35,
        aspect=3.2,
        palette=rule_palette_labels,
        sharey=False
    )
    g.map_dataframe(sns.lineplot, x='week', y='survival_prob', linewidth=2)
    g.map_dataframe(sns.scatterplot, x='week', y='survival_prob', s=18, alpha=0.6)
    g.set_axis_labels('Week', 'Survival Probability')
    g.set_titles(row_template='{row_name}')
    g.add_legend(title='Rule')
    g.fig.subplots_adjust(hspace=0.45)
    g.fig.suptitle('Dynamic Cases: Survival Probability by Rule', y=1.02)
    fig4_path = fig_dir / f'task2_dynamic_cases_survival_{run_ts}.png'
    g.savefig(fig4_path, dpi=300)

    summary = {
        'run_timestamp': run_ts,
        'focus_season': focus_season,
        'outputs': {
            'dynamic_metrics_rule_strategy': str(metrics_path),
            'dynamic_metrics_rule_default': str(default_path),
            'dynamic_elim_prob_weekly': str(elim_probs_path),
            'dynamic_survival_focus': str(survival_path),
        },
        'figures': [
            str(fig1_path),
            str(fig2_path),
            str(fig3_path),
            str(fig4_path),
        ],
    }
    summary_path = log_dir / f'task2_step3_post_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Task2 Step3 Postprocess Report',
        f'- run_timestamp: {run_ts}',
        f'- focus_season: {focus_season}',
        '## Outputs',
        f'- {metrics_path}',
        f'- {default_path}',
        f'- {elim_probs_path}',
        f'- {survival_path}',
        '## Figures',
        f'- {fig1_path}',
        f'- {fig2_path}',
        f'- {fig3_path}',
        f'- {fig4_path}',
    ]
    report_path = log_dir / f'task2_step3_post_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Task2 Step3 postprocess complete: %s', default_path)


if __name__ == '__main__':
    main()
