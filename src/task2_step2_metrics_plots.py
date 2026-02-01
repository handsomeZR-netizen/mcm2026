import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from dwts_rules import compute_judge_rank, bottom_two


def parse_name_set(names: str):
    if pd.isna(names):
        return set()
    parts = [p.strip() for p in str(names).split(' | ')]
    return {p for p in parts if p}


def fit_dirichlet_from_moments(mu, sd, min_s=5.0, fallback_s=50.0):
    mu = np.asarray(mu, dtype='float64')
    sd = np.asarray(sd, dtype='float64')

    mu = np.clip(mu, 1e-9, None)
    mu = mu / mu.sum()

    var = sd ** 2
    with np.errstate(divide='ignore', invalid='ignore'):
        s_candidates = mu * (1 - mu) / var - 1

    valid = np.isfinite(s_candidates) & (s_candidates > 0)
    used = int(valid.sum())

    if used >= 2:
        s = float(np.median(s_candidates[valid]))
        method = 'median'
    elif used == 1:
        s = float(s_candidates[valid][0])
        method = 'single'
    else:
        s = float(fallback_s)
        method = 'fallback'

    if not np.isfinite(s) or s <= 0:
        s = float(fallback_s)
        method = 'fallback'

    s = max(s, min_s)

    alpha = mu * s
    return alpha, {'s': s, 'method': method, 'n_used': used}


def apply_official_points(df_week, fan_votes):
    fan_votes = pd.Series(fan_votes, index=df_week.index, dtype='float64')
    judge_rank = compute_judge_rank(df_week['judge_total'])
    fan_rank = fan_votes.rank(method='min', ascending=False)

    n = len(df_week)
    judge_points = n - judge_rank + 1
    fan_points = n - fan_rank + 1
    total_points = judge_points + fan_points

    ordered = df_week.copy()
    ordered['_total_points'] = total_points.values
    ordered['_fan_votes'] = fan_votes.values
    ordered['_judge_total'] = df_week['judge_total'].values

    ordered = ordered.sort_values(
        by=['_total_points', '_fan_votes', '_judge_total', 'celebrity_name'],
        ascending=[True, True, True, True],
        kind='mergesort',
    )

    eliminated = ordered.iloc[0]['celebrity_name']
    ordered = ordered.assign(
        judge_rank=judge_rank.values,
        fan_rank=fan_rank.values,
        judge_points=judge_points.values,
        fan_points=fan_points.values,
        combined_points=total_points.values,
    )
    return eliminated, ordered


def bottom_two_official(df_week, fan_votes):
    eliminated, ordered = apply_official_points(df_week, fan_votes)
    bottom = ordered.iloc[:2]['celebrity_name'].tolist()
    return bottom, ordered


def choose_saved(bottom_two_names, df_week, fan_votes, strategy, rng, judge_gap=3.0):
    sub = df_week.set_index('celebrity_name').loc[bottom_two_names]
    fan_series = pd.Series(fan_votes, index=df_week['celebrity_name'].values, dtype='float64')
    fan_sub = fan_series.loc[bottom_two_names]

    names = list(bottom_two_names)
    j1, j2 = float(sub.iloc[0]['judge_total']), float(sub.iloc[1]['judge_total'])
    f1, f2 = float(fan_sub.iloc[0]), float(fan_sub.iloc[1])

    if strategy == 'merit':
        if j1 == j2:
            saved = names[0] if f1 >= f2 else names[1]
        else:
            saved = names[0] if j1 > j2 else names[1]
    elif strategy == 'fan':
        if f1 == f2:
            saved = names[0] if j1 >= j2 else names[1]
        else:
            saved = names[0] if f1 > f2 else names[1]
    elif strategy == 'mix':
        if abs(j1 - j2) > judge_gap:
            saved = names[0] if j1 > j2 else names[1]
        else:
            probs = np.array([f1, f2], dtype='float64')
            if probs.sum() <= 0:
                probs = np.array([0.5, 0.5])
            else:
                probs = probs / probs.sum()
            saved = names[int(rng.choice([0, 1], p=probs))]
    else:
        raise ValueError('Unknown strategy')

    eliminated = names[1] if saved == names[0] else names[0]
    return saved, eliminated


def adaptive_weight(week: int, total_weeks: int, w_min: float = 0.45, w_max: float = 0.55) -> float:
    """Linear weight schedule from w_min to w_max across the season."""
    if total_weeks <= 1:
        return 0.5 * (w_min + w_max)
    return w_min + (w_max - w_min) * (week - 1) / (total_weeks - 1)


def fan_last_name(df_week, fan_votes):
    df = df_week[['celebrity_name', 'judge_total']].copy()
    df['fan_votes'] = fan_votes
    df = df.sort_values(by=['fan_votes', 'judge_total', 'celebrity_name'], ascending=[True, True, True])
    return df.iloc[0]['celebrity_name']


def kendall_tau(x, y):
    x = np.asarray(x)
    y = np.asarray(y)
    n = len(x)
    if n < 2:
        return np.nan
    concordant = 0
    discordant = 0
    for i in range(n - 1):
        dx = x[i] - x[i + 1:]
        dy = y[i] - y[i + 1:]
        prod = dx * dy
        concordant += int(np.sum(prod > 0))
        discordant += int(np.sum(prod < 0))
    denom = concordant + discordant
    if denom == 0:
        return np.nan
    return (concordant - discordant) / denom


def main():
    parser = argparse.ArgumentParser(description='Task2 Step2: Metrics + plots')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--posterior', default='data/processed/abc_weekly_posterior.csv')
    parser.add_argument('--sim-raw', default='data/processed/task2_sim_raw.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--fig-dir', default='figures')
    parser.add_argument('--log-dir', default='outputs/task2')
    parser.add_argument('--num-sim', type=int, default=200)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--judge-gap', type=float, default=3.0)
    parser.add_argument('--focus-season', type=int, default=27)
    parser.add_argument('--w-min', type=float, default=0.45)
    parser.add_argument('--w-max', type=float, default=0.55)
    parser.add_argument('--tag', default='')
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    posterior = pd.read_csv(args.posterior)
    sim_raw = pd.read_csv(args.sim_raw)

    out_dir = Path(args.out_dir)
    fig_dir = Path(args.fig_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    tag_suffix = f"_{args.tag}" if args.tag else ''
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_dir / f'task2_step2_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    # --- Consistency from sim_raw ---
    unique_truth = sim_raw['true_elim_names'].dropna().unique()
    truth_map = {name: parse_name_set(name) for name in unique_truth}
    elim = sim_raw['eliminated'].values
    true_names = sim_raw['true_elim_names'].values
    is_hit = [e in truth_map.get(t, set()) for e, t in zip(elim, true_names)]
    sim_raw['is_hit'] = is_hit

    cons_rule = (
        sim_raw.groupby(['rule', 'strategy', 'judges_save'], as_index=False)
        .agg(consistency=('is_hit', 'mean'), sims=('is_hit', 'size'))
    )
    cons_rule_path = out_dir / f'task2_consistency_rule_strategy{tag_suffix}.csv'
    cons_rule.to_csv(cons_rule_path, index=False)

    # --- Resimulation for FII/TPI ---
    truth_eval = truth[truth['has_elim']].copy()
    season_weeks = truth.groupby('season', as_index=False)['week'].max()
    season_weeks = dict(zip(season_weeks['season'], season_weeks['week']))

    rules = ['rank', 'percent', 'adaptive_percent', 'official']
    strategies = ['merit', 'fan', 'mix']

    counts = {}
    counts_season = {}
    skipped_multi = 0

    rng = np.random.default_rng(args.seed)

    for _, t in truth_eval.iterrows():
        season = int(t['season'])
        week = int(t['week'])
        n_elim = int(t.get('n_elim', 1))
        rule_period = t.get('rule_period', 'unknown')
        judges_save = bool(rule_period == 'bottom_two')
        total_weeks = int(season_weeks.get(season, week))
        w_t = adaptive_weight(week, total_weeks, w_min=args.w_min, w_max=args.w_max)

        df_week = weekly[(weekly['season'] == season) & (weekly['week'] == week) & (weekly['active_in_week'])].copy()
        post_week = posterior[(posterior['season'] == season) & (posterior['week'] == week)].copy()
        if df_week.empty or post_week.empty:
            continue

        df_week = df_week.set_index('celebrity_name')
        post_week = post_week.set_index('celebrity_name')
        common = df_week.index.intersection(post_week.index)
        df_week = df_week.loc[common].copy()
        post_week = post_week.loc[common].copy()

        judge_rank = compute_judge_rank(df_week['judge_total'])
        top3_set = set(df_week.loc[judge_rank <= 3].index)

        mu = post_week['posterior_mean'].values
        sd = post_week['posterior_sd'].values
        alpha, _meta = fit_dirichlet_from_moments(mu, sd)
        samples = rng.dirichlet(alpha, size=args.num_sim)

        df_week = df_week.reset_index()

        if n_elim != 1:
            skipped_multi += 1
            continue

        for sim_id in range(args.num_sim):
            fan_votes = samples[sim_id, :]
            fan_last = fan_last_name(df_week, fan_votes)

            for rule in rules:
                if rule == 'rank':
                    bottom_two_names, ordered = bottom_two(df_week, fan_votes, rule='rank')
                elif rule == 'percent':
                    bottom_two_names, ordered = bottom_two(df_week, fan_votes, rule='percent')
                elif rule == 'adaptive_percent':
                    bottom_two_names, ordered = bottom_two(df_week, fan_votes, rule='adaptive_percent', weight=w_t)
                else:
                    if judges_save:
                        bottom_two_names, ordered = bottom_two_official(df_week, fan_votes)
                    else:
                        _eliminated, ordered = apply_official_points(df_week, fan_votes)
                        bottom_two_names = ordered.iloc[:2]['celebrity_name'].tolist()

                if not judges_save:
                    eliminated = ordered.iloc[0]['celebrity_name']
                    key = (rule, 'none', False)
                    counts[key] = counts.get(key, {'total': 0, 'fii': 0, 'tpi': 0})
                    counts[key]['total'] += 1
                    counts[key]['fii'] += int(eliminated == fan_last)
                    counts[key]['tpi'] += int(len(set(bottom_two_names) & top3_set) == 0)

                    k2 = (season, rule, 'none', False)
                    counts_season[k2] = counts_season.get(k2, {'total': 0, 'fii': 0, 'tpi': 0})
                    counts_season[k2]['total'] += 1
                    counts_season[k2]['fii'] += int(eliminated == fan_last)
                    counts_season[k2]['tpi'] += int(len(set(bottom_two_names) & top3_set) == 0)
                else:
                    for strategy in strategies:
                        _saved, eliminated = choose_saved(
                            bottom_two_names,
                            df_week,
                            fan_votes,
                            strategy,
                            rng,
                            judge_gap=args.judge_gap,
                        )
                        key = (rule, strategy, True)
                        counts[key] = counts.get(key, {'total': 0, 'fii': 0, 'tpi': 0})
                        counts[key]['total'] += 1
                        counts[key]['fii'] += int(eliminated == fan_last)
                        counts[key]['tpi'] += int(len(set(bottom_two_names) & top3_set) == 0)

                        k2 = (season, rule, strategy, True)
                        counts_season[k2] = counts_season.get(k2, {'total': 0, 'fii': 0, 'tpi': 0})
                        counts_season[k2]['total'] += 1
                        counts_season[k2]['fii'] += int(eliminated == fan_last)
                        counts_season[k2]['tpi'] += int(len(set(bottom_two_names) & top3_set) == 0)

    metric_rows = []
    for (rule, strategy, judges_save), stats in counts.items():
        metric_rows.append({
            'rule': rule,
            'strategy': strategy,
            'judges_save': judges_save,
            'sims': stats['total'],
            'FII': stats['fii'] / stats['total'] if stats['total'] else np.nan,
            'TPI': stats['tpi'] / stats['total'] if stats['total'] else np.nan,
        })

    metrics_rule = pd.DataFrame(metric_rows)
    metrics_rule_path = out_dir / f'task2_metrics_rule_strategy{tag_suffix}.csv'
    metrics_rule.to_csv(metrics_rule_path, index=False)

    metric_rows_season = []
    for (season, rule, strategy, judges_save), stats in counts_season.items():
        metric_rows_season.append({
            'season': season,
            'rule': rule,
            'strategy': strategy,
            'judges_save': judges_save,
            'sims': stats['total'],
            'FII': stats['fii'] / stats['total'] if stats['total'] else np.nan,
            'TPI': stats['tpi'] / stats['total'] if stats['total'] else np.nan,
        })

    metrics_season = pd.DataFrame(metric_rows_season)
    metrics_season_path = out_dir / f'task2_metrics_season{tag_suffix}.csv'
    metrics_season.to_csv(metrics_season_path, index=False)

    # --- Default policy: mix for save weeks, none for non-save weeks ---
    def_policy = metrics_rule.copy()
    cons_policy = cons_rule.copy()

    def_policy['policy'] = np.where(def_policy['judges_save'], def_policy['strategy'], 'none')
    cons_policy['policy'] = np.where(cons_policy['judges_save'], cons_policy['strategy'], 'none')

    def_policy = def_policy[def_policy['policy'].isin(['none', 'mix'])]
    cons_policy = cons_policy[cons_policy['policy'].isin(['none', 'mix'])]

    def_policy['FII_weighted'] = def_policy['FII'] * def_policy['sims']
    def_policy['TPI_weighted'] = def_policy['TPI'] * def_policy['sims']
    def_policy = (
        def_policy.groupby(['rule'], as_index=False)
        .agg(
            sims=('sims', 'sum'),
            FII_weighted=('FII_weighted', 'sum'),
            TPI_weighted=('TPI_weighted', 'sum')
        )
    )
    def_policy['FII'] = def_policy['FII_weighted'] / def_policy['sims']
    def_policy['TPI'] = def_policy['TPI_weighted'] / def_policy['sims']
    def_policy = def_policy[['rule', 'sims', 'FII', 'TPI']]

    cons_policy['cons_weighted'] = cons_policy['consistency'] * cons_policy['sims']
    cons_policy = (
        cons_policy.groupby(['rule'], as_index=False)
        .agg(
            sims=('sims', 'sum'),
            cons_weighted=('cons_weighted', 'sum')
        )
    )
    cons_policy['consistency'] = cons_policy['cons_weighted'] / cons_policy['sims']
    cons_policy = cons_policy[['rule', 'consistency', 'sims']]

    metrics_default = def_policy.merge(cons_policy[['rule', 'consistency']], on='rule', how='left')
    metrics_default_path = out_dir / f'task2_metrics_rule_default{tag_suffix}.csv'
    metrics_default.to_csv(metrics_default_path, index=False)

    # --- Elimination probability by week ---
    sim_counts = (
        sim_raw.groupby(['rule', 'strategy', 'season', 'week']).size().rename('sim_n').reset_index()
    )
    elim_counts = (
        sim_raw.groupby(['rule', 'strategy', 'season', 'week', 'eliminated']).size().rename('elim_n').reset_index()
    )
    elim_probs = elim_counts.merge(sim_counts, on=['rule', 'strategy', 'season', 'week'], how='left')
    elim_probs['elim_prob'] = elim_probs['elim_n'] / elim_probs['sim_n']
    elim_probs_path = out_dir / f'task2_elim_prob_weekly{tag_suffix}.csv'
    elim_probs.to_csv(elim_probs_path, index=False)

    # --- Survival for focus season (default mix policy) ---
    focus_season = args.focus_season
    active = weekly[
        (weekly['season'] == focus_season) & (weekly['active_in_week'])
    ][['season', 'week', 'celebrity_name', 'placement']].drop_duplicates()

    mix_probs = elim_probs[(elim_probs['season'] == focus_season) & (
        ((elim_probs['strategy'] == 'mix') | (elim_probs['strategy'] == 'none'))
    )]

    mix_probs = mix_probs.merge(
        truth[['season', 'week', 'rule_period']],
        on=['season', 'week'],
        how='left'
    )
    mix_probs['use'] = np.where(mix_probs['rule_period'] == 'bottom_two', mix_probs['strategy'] == 'mix', mix_probs['strategy'] == 'none')
    mix_probs = mix_probs[mix_probs['use']]

    survival_rows = []
    for rule in rules:
        rule_probs = mix_probs[mix_probs['rule'] == rule].copy()
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
    survival_path = out_dir / f'task2_survival_weekly_focus{tag_suffix}.csv'
    survival_df.to_csv(survival_path, index=False)

    # --- Kendall Tau between rule rankings (approx) ---
    tau_rows = []
    for season in sorted(sim_raw['season'].unique()):
        season_probs = elim_probs[elim_probs['season'] == season].copy()
        season_probs = season_probs.merge(
            truth[['season', 'week', 'rule_period']],
            on=['season', 'week'],
            how='left'
        )
        season_probs['use'] = np.where(season_probs['rule_period'] == 'bottom_two', season_probs['strategy'] == 'mix', season_probs['strategy'] == 'none')
        season_probs = season_probs[season_probs['use']]

        expected = {}
        for rule in rules:
            rule_probs = season_probs[season_probs['rule'] == rule].copy()
            if rule_probs.empty:
                continue
            pivot = (
                rule_probs.groupby(['week', 'eliminated'])['elim_prob'].sum().reset_index()
            )
            pivot = pivot.rename(columns={'eliminated': 'celebrity_name'})
            pivot = pivot.merge(
                weekly[weekly['season'] == season][['season', 'week', 'celebrity_name']].drop_duplicates(),
                on=['week', 'celebrity_name'],
                how='right'
            )
            pivot['elim_prob'] = pivot['elim_prob'].fillna(0.0)

            exp_week = (
                pivot.groupby('celebrity_name')
                .apply(lambda df: np.average(df['week'], weights=df['elim_prob']) if df['elim_prob'].sum() > 0 else np.nan)
            )
            exp_week = exp_week.to_frame('expected_week')
            season_last = int(truth[truth['season'] == season]['season_last_week'].max())
            exp_week['expected_week'] = exp_week['expected_week'].fillna(season_last + 1)
            exp_week = exp_week.reset_index()
            exp_week = exp_week.sort_values(by=['expected_week', 'celebrity_name'])
            exp_week['rank'] = np.arange(1, len(exp_week) + 1)
            expected[rule] = exp_week[['celebrity_name', 'rank']]

        if len(expected) < 2:
            continue

        rule_pairs = [
            ('rank', 'percent'),
            ('rank', 'official'),
            ('percent', 'official'),
            ('adaptive_percent', 'percent'),
            ('adaptive_percent', 'rank'),
            ('adaptive_percent', 'official'),
        ]
        for a, b in rule_pairs:
            if a not in expected or b not in expected:
                continue
            merged = expected[a].merge(expected[b], on='celebrity_name', how='inner', suffixes=('_a', '_b'))
            tau = kendall_tau(merged['rank_a'].values, merged['rank_b'].values)
            tau_rows.append({
                'season': season,
                'pair': f'{a}_vs_{b}',
                'kendall_tau': tau,
            })

    tau_df = pd.DataFrame(tau_rows)
    tau_path = out_dir / f'task2_kendall_tau{tag_suffix}.csv'
    tau_df.to_csv(tau_path, index=False)

    tau_summary = (
        tau_df.groupby('pair', as_index=False)
        .agg(
            tau_mean=('kendall_tau', 'mean'),
            tau_median=('kendall_tau', 'median')
        )
    )
    tau_summary_path = out_dir / f'task2_kendall_tau_summary{tag_suffix}.csv'
    tau_summary.to_csv(tau_summary_path, index=False)

    # --- Plot settings ---
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

    # Plot 1: Rule bias radar (default policy)
    radar = metrics_default.set_index('rule').reindex(rule_order)
    labels = ['Consistency', 'FII', 'TPI']
    values = radar[['consistency', 'FII', 'TPI']].values

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig1 = plt.figure(figsize=(6.4, 5.4))
    ax1 = plt.subplot(111, polar=True)

    for i, rule in enumerate(rule_order):
        vals = values[i].tolist()
        vals += vals[:1]
        ax1.plot(angles, vals, color=rule_palette[rule], linewidth=2, label=rule_labels[rule])
        ax1.fill(angles, vals, color=rule_palette[rule], alpha=0.15)

    ax1.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax1.set_ylim(0, 1)
    ax1.set_title('Rule Bias Profile (Default: Mix Save)', pad=18)
    ax1.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
    fig1.tight_layout()
    fig1_path = fig_dir / f'task2_rule_bias_radar_{run_ts}{tag_suffix}.png'
    fig1.savefig(fig1_path, dpi=300)

    # Plot 2: Kendall Tau heatmap (average)
    tau_mat = pd.DataFrame(
        np.eye(len(rule_order)),
        index=[rule_labels[r] for r in rule_order],
        columns=[rule_labels[r] for r in rule_order],
    )
    for _, row in tau_summary.iterrows():
        a, b = row['pair'].split('_vs_')
        tau_mat.loc[rule_labels[a], rule_labels[b]] = row['tau_mean']
        tau_mat.loc[rule_labels[b], rule_labels[a]] = row['tau_mean']

    fig2, ax2 = plt.subplots(figsize=(5.6, 4.6))
    sns.heatmap(
        tau_mat,
        cmap='crest',
        vmin=0,
        vmax=1,
        annot=True,
        fmt='.2f',
        linewidths=0.5,
        cbar_kws={'label': 'Kendall Tau (Avg)'}
    )
    ax2.set_title('Outcome Divergence Across Rules')
    ax2.set_xlabel('Rule')
    ax2.set_ylabel('Rule')
    fig2.tight_layout()
    fig2_path = fig_dir / f'task2_kendall_tau_heatmap_{run_ts}{tag_suffix}.png'
    fig2.savefig(fig2_path, dpi=300)

    # Plot 3: Survival heatmap for focus season
    fig3, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 7.5), sharex=True)
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
        ax.set_title(f'Season {focus_season} Survival (Rule: {rule_labels[rule]})')
        ax.set_ylabel('Contestant')
    axes[-1].set_xlabel('Week')
    fig3.tight_layout()
    fig3_path = fig_dir / f'task2_survival_heatmap_s{focus_season}_{run_ts}{tag_suffix}.png'
    fig3.savefig(fig3_path, dpi=300)

    # Plot 4: Controversial cases survival lines
    cases = ['Jerry Rice', 'Billy Ray Cyrus', 'Bristol Palin', 'Bobby Bones']
    case_rows = []
    for rule in rules:
        df_rule = elim_probs[elim_probs['rule'] == rule].copy()
        df_rule = df_rule.merge(
            truth[['season', 'week', 'rule_period']],
            on=['season', 'week'],
            how='left'
        )
        df_rule['use'] = np.where(df_rule['rule_period'] == 'bottom_two', df_rule['strategy'] == 'mix', df_rule['strategy'] == 'none')
        df_rule = df_rule[df_rule['use']]
        df_rule = df_rule[df_rule['eliminated'].isin(cases)]
        df_rule['survival_prob'] = 1.0 - df_rule['elim_prob']
        df_rule['rule_label'] = df_rule['rule'].map(rule_labels)
        case_rows.append(df_rule)

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
    g.fig.suptitle('Controversial Cases: Survival Probability by Rule', y=1.02)
    fig4_path = fig_dir / f'task2_cases_survival_{run_ts}{tag_suffix}.png'
    g.savefig(fig4_path, dpi=300)

    # Plot 5: Consistency bar (default policy)
    fig5, ax5 = plt.subplots(figsize=(6.2, 4.2))
    plot_df = metrics_default.copy()
    plot_df['rule_label'] = plot_df['rule'].map(rule_labels)
    sns.barplot(
        data=plot_df,
        x='rule_label',
        y='consistency',
        hue='rule_label',
        palette=rule_palette_labels,
        ax=ax5,
        legend=False
    )
    ax5.set_ylim(0, 1)
    ax5.set_title('Consistency vs Reality (Default Save Strategy)')
    ax5.set_xlabel('Rule')
    ax5.set_ylabel('Consistency')
    fig5.tight_layout()
    fig5_path = fig_dir / f'task2_consistency_bar_{run_ts}{tag_suffix}.png'
    fig5.savefig(fig5_path, dpi=300)

    summary = {
        'run_timestamp': run_ts,
        'focus_season': focus_season,
        'num_sim': args.num_sim,
        'seed': args.seed,
        'w_min': args.w_min,
        'w_max': args.w_max,
        'tag': args.tag,
        'skipped_multi_elim_weeks': int(skipped_multi),
        'outputs': {
            'metrics_rule_strategy': str(metrics_rule_path),
            'metrics_rule_default': str(metrics_default_path),
            'metrics_season': str(metrics_season_path),
            'consistency_rule_strategy': str(cons_rule_path),
            'elim_prob_weekly': str(elim_probs_path),
            'survival_focus': str(survival_path),
            'kendall_tau': str(tau_path),
            'kendall_tau_summary': str(tau_summary_path),
        },
        'figures': [
            str(fig1_path),
            str(fig2_path),
            str(fig3_path),
            str(fig4_path),
            str(fig5_path),
        ],
    }
    summary_path = log_dir / f'task2_step2_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Task2 Step2 Report',
        f'- run_timestamp: {run_ts}',
        f'- focus_season: {focus_season}',
        f'- num_sim: {args.num_sim}',
        f'- w_min: {args.w_min}',
        f'- w_max: {args.w_max}',
        f'- tag: {args.tag or "(none)"}',
        f'- skipped_multi_elim_weeks: {skipped_multi}',
        '## Outputs',
        f'- {metrics_rule_path}',
        f'- {metrics_default_path}',
        f'- {metrics_season_path}',
        f'- {cons_rule_path}',
        f'- {elim_probs_path}',
        f'- {survival_path}',
        f'- {tau_path}',
        f'- {tau_summary_path}',
        '## Figures',
        f'- {fig1_path}',
        f'- {fig2_path}',
        f'- {fig3_path}',
        f'- {fig4_path}',
        f'- {fig5_path}',
    ]
    report_path = log_dir / f'task2_step2_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Task2 Step2 complete: %s', metrics_default_path)


if __name__ == '__main__':
    main()
