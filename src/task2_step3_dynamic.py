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


def build_similarity(info_df):
    info = info_df.copy()
    info['celebrity_age_during_season'] = pd.to_numeric(info['celebrity_age_during_season'], errors='coerce')
    age_med = info['celebrity_age_during_season'].median()
    info['age_filled'] = info['celebrity_age_during_season'].fillna(age_med)
    age_z = (info['age_filled'] - info['age_filled'].mean()) / (info['age_filled'].std() + 1e-9)
    info['age_z'] = age_z

    dummies = pd.get_dummies(info['celebrity_industry'], prefix='industry', dummy_na=True)
    features = pd.concat([dummies, info[['age_z']]], axis=1)

    X = features.values.astype('float64')
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    sim = (X @ X.T) / (norms * norms.T + 1e-9)
    sim = np.clip(sim, 0.0, 1.0)

    names = info['celebrity_name'].tolist()
    index = {name: i for i, name in enumerate(names)}
    return names, index, sim


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


def redistribute_votes(names_all, names_alive, mu_map, sim_names, sim_index, sim_matrix, loss_rate=0.0):
    alive_set = set(names_alive)
    mu_alive = {name: mu_map.get(name, 0.0) for name in names_alive}
    loss_rate = float(np.clip(loss_rate, 0.0, 0.9))

    base_weights = np.array([mu_alive.get(n, 0.0) for n in names_alive], dtype='float64')
    if base_weights.sum() <= 0:
        base_weights = np.ones(len(names_alive), dtype='float64')
    base_weights = base_weights / base_weights.sum()

    removed = [name for name in names_all if name not in alive_set]
    for name in removed:
        share = mu_map.get(name, 0.0)
        if share <= 0:
            continue
        transfer_share = share * (1.0 - loss_rate)
        loss_share = share * loss_rate
        if name not in sim_index:
            weights = np.ones(len(names_alive), dtype='float64')
        else:
            idx = sim_index[name]
            alive_indices = [sim_index[n] for n in names_alive if n in sim_index]
            if len(alive_indices) != len(names_alive):
                weights = np.ones(len(names_alive), dtype='float64')
            else:
                weights = sim_matrix[idx, alive_indices].astype('float64')
        if weights.sum() <= 0:
            weights = np.ones(len(names_alive), dtype='float64')
        weights = weights / weights.sum()
        for i, alive_name in enumerate(names_alive):
            mu_alive[alive_name] = mu_alive.get(alive_name, 0.0) + transfer_share * weights[i]
            mu_alive[alive_name] = mu_alive.get(alive_name, 0.0) + loss_share * base_weights[i]

    total = sum(mu_alive.values())
    if total <= 0:
        uniform = 1.0 / max(len(names_alive), 1)
        return {name: uniform for name in names_alive}

    return {name: val / total for name, val in mu_alive.items()}


def main():
    parser = argparse.ArgumentParser(description='Task2 Step3: Dynamic counterfactual simulation + policy plots')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--posterior', default='data/processed/abc_weekly_posterior.csv')
    parser.add_argument('--alpha-summary', default='data/processed/task2_alpha_fit_summary.csv')
    parser.add_argument('--frozen-metrics', default='data/processed/task2_metrics_rule_default.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--fig-dir', default='figures')
    parser.add_argument('--log-dir', default='outputs/task2')
    parser.add_argument('--num-sim', type=int, default=120)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--judge-gap', type=float, default=3.0)
    parser.add_argument('--zombie-decay', type=float, default=0.9)
    parser.add_argument('--loss-rate', type=float, default=0.0)
    parser.add_argument('--focus-season', type=int, default=27)
    parser.add_argument('--strategy-scope', choices=['all', 'mix'], default='all')
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    posterior = pd.read_csv(args.posterior)
    alpha_summary = pd.read_csv(args.alpha_summary)
    frozen_metrics = pd.read_csv(args.frozen_metrics)

    out_dir = Path(args.out_dir)
    fig_dir = Path(args.fig_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    loss_tag = f"loss{args.loss_rate:.2f}".replace('.', 'p')
    tag = f"{loss_tag}_{args.strategy_scope}_n{args.num_sim}"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_dir / f'task2_step3_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    rng = np.random.default_rng(args.seed)

    alpha_map = {
        (int(row['season']), int(row['week'])): float(row['s_concentration'])
        for _, row in alpha_summary.iterrows()
    }

    # Precompute last observed stats for zombies
    last_judge = (
        weekly[weekly['active_in_week']]
        .sort_values(['season', 'week'])
        .groupby(['season', 'celebrity_name'], as_index=False)
        .tail(1)
        .set_index(['season', 'celebrity_name'])
    )

    last_mu = (
        posterior.sort_values(['season', 'week'])
        .groupby(['season', 'celebrity_name'], as_index=False)
        .tail(1)
        .set_index(['season', 'celebrity_name'])
    )

    # roster by season-week
    weekly_active = weekly[weekly['active_in_week']].copy()
    roster_map = {
        (int(s), int(w)): df
        for (s, w), df in weekly_active.groupby(['season', 'week'])
    }

    posterior_map = {
        (int(s), int(w)): df
        for (s, w), df in posterior.groupby(['season', 'week'])
    }

    rules = ['rank', 'percent', 'adaptive_percent', 'official']
    strategies = ['mix'] if args.strategy_scope == 'mix' else ['merit', 'fan', 'mix']

    rows = []
    skipped_multi = 0

    for season, season_truth in truth.groupby('season'):
        season = int(season)
        weeks = sorted(season_truth['week'].unique())
        total_weeks = int(max(weeks)) if weeks else 1

        info = weekly[weekly['season'] == season][[
            'celebrity_name', 'celebrity_industry', 'celebrity_age_during_season'
        ]].drop_duplicates()

        if info.empty:
            continue

        sim_names, sim_index, sim_matrix = build_similarity(info)

        # initial roster from first week in season
        first_week = min(weeks)
        base_df = roster_map.get((season, int(first_week)))
        if base_df is None or base_df.empty:
            continue

        base_roster = base_df['celebrity_name'].unique().tolist()

        for rule in rules:
            for strategy in strategies:
                for sim_id in range(args.num_sim):
                    alive = set(base_roster)

                    for week in weeks:
                        week = int(week)
                        w_t = adaptive_weight(week, total_weeks)
                        trow = season_truth[season_truth['week'] == week].iloc[0]
                        has_elim = bool(trow['has_elim'])
                        n_elim = int(trow.get('n_elim', 1))
                        rule_period = trow.get('rule_period', 'unknown')
                        judges_save = bool(rule_period == 'bottom_two')

                        base_df = roster_map.get((season, week))
                        if base_df is None or base_df.empty:
                            continue

                        base_roster = base_df['celebrity_name'].unique().tolist()
                        alive_in_week = [name for name in base_roster if name in alive]
                        zombies = [name for name in alive if name not in base_roster]
                        participants = alive_in_week + zombies

                        if len(participants) < 2:
                            continue

                        # judge scores
                        df_week = base_df[['celebrity_name', 'judge_total']].drop_duplicates().copy()
                        df_week = df_week[df_week['celebrity_name'].isin(alive_in_week)]

                        if zombies:
                            synth_rows = []
                            for name in zombies:
                                key = (season, name)
                                if key in last_judge.index:
                                    judge_total = float(last_judge.loc[key]['judge_total'])
                                else:
                                    judge_total = float(base_df['judge_total'].mean())
                                synth_rows.append({'celebrity_name': name, 'judge_total': judge_total})
                            if synth_rows:
                                df_week = pd.concat([df_week, pd.DataFrame(synth_rows)], ignore_index=True)

                        df_week = df_week.drop_duplicates(subset=['celebrity_name'])

                        # mu for base roster + zombies
                        mu_map = {}
                        post_df = posterior_map.get((season, week))
                        if post_df is not None:
                            for _, prow in post_df.iterrows():
                                mu_map[prow['celebrity_name']] = float(prow['posterior_mean'])

                        for name in zombies:
                            key = (season, name)
                            if key in last_mu.index:
                                last_week = int(last_mu.loc[key]['week'])
                                last_share = float(last_mu.loc[key]['posterior_mean'])
                                decay = args.zombie_decay ** max(0, week - last_week)
                                mu_map[name] = last_share * decay
                            else:
                                mu_map[name] = 0.0

                        # include base roster even if eliminated (for redistribution)
                        all_names = list(dict.fromkeys(base_roster + zombies))
                        mu_map = {name: float(mu_map.get(name, 0.0)) for name in all_names}

                        mu_alive_map = redistribute_votes(
                            names_all=all_names,
                            names_alive=participants,
                            mu_map=mu_map,
                            sim_names=sim_names,
                            sim_index=sim_index,
                            sim_matrix=sim_matrix,
                            loss_rate=args.loss_rate,
                        )

                        mu_alive = np.array([mu_alive_map[n] for n in participants], dtype='float64')
                        if mu_alive.sum() <= 0:
                            mu_alive = np.ones(len(participants), dtype='float64') / len(participants)

                        s = alpha_map.get((season, week), 50.0)
                        alpha = mu_alive * max(s, 5.0)

                        fan_votes = rng.dirichlet(alpha)
                        fan_last = fan_last_name(df_week, fan_votes)

                        if not has_elim:
                            continue

                        if n_elim != 1:
                            skipped_multi += 1
                            continue

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
                                _elim, ordered = apply_official_points(df_week, fan_votes)
                                bottom_two_names = ordered.iloc[:2]['celebrity_name'].tolist()

                        if judges_save:
                            saved, eliminated = choose_saved(
                                bottom_two_names,
                                df_week,
                                fan_votes,
                                strategy,
                                rng,
                                judge_gap=args.judge_gap,
                            )
                        else:
                            saved = ''
                            eliminated = ordered.iloc[0]['celebrity_name']

                        # update alive
                        if eliminated in alive:
                            alive.remove(eliminated)

                        judge_rank = compute_judge_rank(df_week.set_index('celebrity_name')['judge_total'])
                        top3_set = set(judge_rank[judge_rank <= 3].index)
                        top3_safe = int(len(set(bottom_two_names) & top3_set) == 0)

                        true_names = parse_name_set(trow['elim_names'])
                        is_hit = int(eliminated in true_names) if true_names else np.nan

                        rows.append({
                            'season': season,
                            'week': week,
                            'sim_id': sim_id,
                            'rule': rule,
                            'strategy': strategy,
                            'judges_save': judges_save,
                            'bottom_two': ' | '.join(bottom_two_names),
                            'saved': saved,
                            'eliminated': eliminated,
                            'true_elim_names': trow['elim_names'],
                            'n_elim': n_elim,
                            'rule_period': rule_period,
                            'fan_last': fan_last,
                            'top3_safe': top3_safe,
                            'is_hit': is_hit,
                        })

    sim_df = pd.DataFrame(rows)
    sim_path = out_dir / f'task2_dynamic_sim_raw_{tag}.csv'
    sim_df.to_csv(sim_path, index=False)

    # Metrics
    sim_df['is_fan_last'] = (sim_df['eliminated'] == sim_df['fan_last']).astype(int)

    metrics = (
        sim_df.groupby(['rule', 'strategy', 'judges_save'], as_index=False)
        .agg(
            sims=('season', 'size'),
            consistency=('is_hit', 'mean'),
            FII=('is_fan_last', 'mean'),
            TPI=('top3_safe', 'mean'),
        )
    )
    metrics_path = out_dir / f'task2_dynamic_metrics_rule_strategy_{tag}.csv'
    metrics.to_csv(metrics_path, index=False)

    # Default policy metrics
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

    default_path = out_dir / f'task2_dynamic_metrics_rule_default_{tag}.csv'
    default_metrics.to_csv(default_path, index=False)

    # Elimination probability by week
    sim_counts = (
        sim_df.groupby(['rule', 'strategy', 'season', 'week']).size().rename('sim_n').reset_index()
    )
    elim_counts = (
        sim_df.groupby(['rule', 'strategy', 'season', 'week', 'eliminated']).size().rename('elim_n').reset_index()
    )
    elim_probs = elim_counts.merge(sim_counts, on=['rule', 'strategy', 'season', 'week'], how='left')
    elim_probs['elim_prob'] = elim_probs['elim_n'] / elim_probs['sim_n']
    elim_probs_path = out_dir / f'task2_dynamic_elim_prob_weekly_{tag}.csv'
    elim_probs.to_csv(elim_probs_path, index=False)

    # Survival heatmap for focus season (default policy)
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
    survival_path = out_dir / f'task2_dynamic_survival_weekly_focus_{tag}.csv'
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
    fig1, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 7.5), sharex=True)
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
    fig1_path = fig_dir / f'task2_dynamic_survival_heatmap_s{focus_season}_{tag}_{run_ts}.png'
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
    fig2_path = fig_dir / f'task2_policy_frontier_{tag}_{run_ts}.png'
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
    fig3_path = fig_dir / f'task2_dynamic_consistency_bar_{tag}_{run_ts}.png'
    fig3.savefig(fig3_path, dpi=300)

    # Plot D: Dynamic controversial cases
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
    fig4_path = fig_dir / f'task2_dynamic_cases_survival_{tag}_{run_ts}.png'

    # Plot E: Season storyline (top 6 by placement)
    top6 = (
        active[['celebrity_name', 'placement']]
        .drop_duplicates()
        .sort_values(by=['placement', 'celebrity_name'])
        .head(6)
    )
    storyline = survival_df[survival_df['celebrity_name'].isin(top6['celebrity_name'])].copy()
    storyline['rule_label'] = storyline['rule'].map(rule_labels)
    g2 = sns.relplot(
        data=storyline,
        x='week', y='survival_prob',
        hue='celebrity_name', col='rule_label',
        kind='line', height=3.1, aspect=1.15,
        palette=sns.color_palette('mako', n_colors=top6.shape[0]),
        facet_kws=dict(sharey=True)
    )
    g2.set_axis_labels('Week', 'Survival Probability')
    g2.set_titles('{col_name}')
    g2.fig.suptitle(f'Season {focus_season} Storyline (Top 6 by Placement)', y=1.04)
    fig5_path = fig_dir / f'task2_storyline_s{focus_season}_{tag}_{run_ts}.png'
    g2.savefig(fig5_path, dpi=300)
    g.savefig(fig4_path, dpi=300)

    summary = {
        'run_timestamp': run_ts,
        'num_sim': args.num_sim,
        'seed': args.seed,
        'focus_season': focus_season,
        'skipped_multi_elim_weeks': int(skipped_multi),
        'loss_rate': float(args.loss_rate),
        'strategy_scope': args.strategy_scope,
        'tag': tag,
        'outputs': {
            'dynamic_sim_raw': str(sim_path),
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
            str(fig5_path),
        ],
    }
    summary_path = log_dir / f'task2_step3_summary_{tag}_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Task2 Step3 Report',
        f'- run_timestamp: {run_ts}',
        f'- num_sim: {args.num_sim}',
        f'- focus_season: {focus_season}',
        f'- skipped_multi_elim_weeks: {skipped_multi}',
        f'- loss_rate: {args.loss_rate}',
        f'- strategy_scope: {args.strategy_scope}',
        f'- tag: {tag}',
        '## Outputs',
        f'- {sim_path}',
        f'- {metrics_path}',
        f'- {default_path}',
        f'- {elim_probs_path}',
        f'- {survival_path}',
        '## Figures',
        f'- {fig1_path}',
        f'- {fig2_path}',
        f'- {fig3_path}',
        f'- {fig4_path}',
        f'- {fig5_path}',
    ]
    report_path = log_dir / f'task2_step3_report_{tag}_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Task2 Step3 complete: %s', default_path)


if __name__ == '__main__':
    main()
