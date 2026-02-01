import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dwts_rules import (
    compute_fan_rank,
    compute_judge_rank,
    compute_fan_pct,
    compute_judge_pct,
    bottom_two,
)


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
    fan_rank = compute_fan_rank(fan_votes)

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


def main():
    parser = argparse.ArgumentParser(description='Task2 Step1: Counterfactual simulation (Frozen history)')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--posterior', default='data/processed/abc_weekly_posterior.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--log-dir', default='outputs/task2')
    parser.add_argument('--num-sim', type=int, default=200)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--judge-gap', type=float, default=3.0)
    parser.add_argument('--w-min', type=float, default=0.45)
    parser.add_argument('--w-max', type=float, default=0.55)
    parser.add_argument('--tag', default='')
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    posterior = pd.read_csv(args.posterior)

    out_dir = Path(args.out_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_dir / f'task2_step1_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    rng = np.random.default_rng(args.seed)

    truth_eval = truth[truth['has_elim']].copy()
    season_weeks = truth.groupby('season', as_index=False)['week'].max()
    season_weeks = dict(zip(season_weeks['season'], season_weeks['week']))

    rules = ['rank', 'percent', 'adaptive_percent', 'official']
    strategies = ['merit', 'fan', 'mix']

    rows = []
    alpha_rows = []
    fallback_weeks = 0

    for _, t in truth_eval.iterrows():
        season = int(t['season'])
        week = int(t['week'])
        true_elim_names = t['elim_names']
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

        mu = post_week['posterior_mean'].values
        sd = post_week['posterior_sd'].values

        alpha, alpha_meta = fit_dirichlet_from_moments(mu, sd)
        if alpha_meta['method'] == 'fallback':
            fallback_weeks += 1

        alpha_rows.append({
            'season': season,
            'week': week,
            'n_contestants': len(common),
            's_concentration': alpha_meta['s'],
            's_method': alpha_meta['method'],
            's_n_used': alpha_meta['n_used'],
            'rule_period': rule_period,
        })

        samples = rng.dirichlet(alpha, size=args.num_sim)

        df_week = df_week.reset_index()
        for sim_id in range(args.num_sim):
            fan_votes = samples[sim_id, :]

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
                        eliminated, ordered = apply_official_points(df_week, fan_votes)
                        bottom_two_names = ordered.iloc[:2]['celebrity_name'].tolist()

                if not judges_save:
                    eliminated = ordered.iloc[0]['celebrity_name']

                    rows.append({
                        'season': season,
                        'week': week,
                        'sim_id': sim_id,
                        'rule': rule,
                        'judges_save': False,
                        'strategy': 'none',
                        'bottom_two': ' | '.join(bottom_two_names),
                        'saved': '',
                        'eliminated': eliminated,
                        'true_elim_names': true_elim_names,
                        'n_elim': n_elim,
                        'rule_period': rule_period,
                    })
                else:
                    for strategy in strategies:
                        saved, eliminated = choose_saved(
                            bottom_two_names,
                            df_week,
                            fan_votes,
                            strategy,
                            rng,
                            judge_gap=args.judge_gap,
                        )
                        rows.append({
                            'season': season,
                            'week': week,
                            'sim_id': sim_id,
                            'rule': rule,
                            'judges_save': True,
                            'strategy': strategy,
                            'bottom_two': ' | '.join(bottom_two_names),
                            'saved': saved,
                            'eliminated': eliminated,
                            'true_elim_names': true_elim_names,
                            'n_elim': n_elim,
                            'rule_period': rule_period,
                        })

    tag_suffix = f"_{args.tag}" if args.tag else ''

    sim_df = pd.DataFrame(rows)
    out_path = out_dir / f'task2_sim_raw{tag_suffix}.csv'
    sim_df.to_csv(out_path, index=False)

    alpha_df = pd.DataFrame(alpha_rows)
    alpha_path = out_dir / f'task2_alpha_fit_summary{tag_suffix}.csv'
    alpha_df.to_csv(alpha_path, index=False)

    summary = {
        'run_timestamp': run_ts,
        'num_sim_per_week': args.num_sim,
        'seed': args.seed,
        'w_min': args.w_min,
        'w_max': args.w_max,
        'tag': args.tag,
        'weeks_total': int(truth_eval.shape[0]),
        'rows_generated': int(sim_df.shape[0]),
        'alpha_fallback_weeks': int(fallback_weeks),
        'outputs': {
            'task2_sim_raw': str(out_path),
            'task2_alpha_fit_summary': str(alpha_path),
        },
    }
    summary_path = log_dir / f'task2_step1_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Task2 Step1 Report',
        f'- run_timestamp: {run_ts}',
        f'- num_sim_per_week: {args.num_sim}',
        f'- seed: {args.seed}',
        f'- w_min: {args.w_min}',
        f'- w_max: {args.w_max}',
        f'- tag: {args.tag or "(none)"}',
        f'- weeks_total: {truth_eval.shape[0]}',
        f'- rows_generated: {sim_df.shape[0]}',
        f'- alpha_fallback_weeks: {fallback_weeks}',
        '## Outputs',
        f'- {out_path}',
        f'- {alpha_path}',
    ]
    report_path = log_dir / f'task2_step1_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Task2 Step1 complete: %s', out_path)


if __name__ == '__main__':
    main()
