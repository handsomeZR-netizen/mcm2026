import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def run_abc(alpha, df_week, rule, judges_save, true_set, target, max_trials, batch_size, rng):
    n_contestants = len(alpha)
    alpha = np.clip(alpha, 1e-6, None)

    judge_total = df_week['judge_total'].values.astype(float)
    if rule == 'rank':
        judge_rank = pd.Series(judge_total).rank(method='min', ascending=False).values
    else:
        total = judge_total.sum()
        judge_pct = judge_total / total if total > 0 else np.zeros_like(judge_total)

    accepted_chunks = []
    trials = 0

    while sum(len(x) for x in accepted_chunks) < target and trials < max_trials:
        batch = min(batch_size, max_trials - trials)
        votes = rng.dirichlet(alpha, size=batch)
        trials += batch

        if rule == 'rank':
            order = np.argsort(-votes, axis=1)
            ranks = np.empty_like(order, dtype=float)
            ranks[np.arange(batch)[:, None], order] = np.arange(1, n_contestants + 1)
            combined = ranks + judge_rank
            if judges_save:
                bottom_idx = np.argpartition(combined, -2, axis=1)[:, -2:]
                mask = np.zeros(batch, dtype=bool)
                for i in range(batch):
                    names = {df_week.index[bottom_idx[i, 0]], df_week.index[bottom_idx[i, 1]]}
                    if names & true_set:
                        mask[i] = True
            else:
                elim_idx = np.argmax(combined, axis=1)
                pred = [df_week.index[i] for i in elim_idx]
                mask = np.array([p in true_set for p in pred])
        else:
            combined = 0.5 * judge_pct + 0.5 * votes
            if judges_save:
                bottom_idx = np.argpartition(combined, 2, axis=1)[:, :2]
                mask = np.zeros(batch, dtype=bool)
                for i in range(batch):
                    names = {df_week.index[bottom_idx[i, 0]], df_week.index[bottom_idx[i, 1]]}
                    if names & true_set:
                        mask[i] = True
            else:
                elim_idx = np.argmin(combined, axis=1)
                pred = [df_week.index[i] for i in elim_idx]
                mask = np.array([p in true_set for p in pred])

        if mask.any():
            accepted_chunks.append(votes[mask])

    accepted_raw = np.vstack(accepted_chunks) if accepted_chunks else np.empty((0, n_contestants))
    acc_rate = len(accepted_raw) / trials if trials > 0 else 0.0
    if len(accepted_raw) > target:
        accepted = accepted_raw[:target]
    else:
        accepted = accepted_raw

    if len(accepted) > 0:
        mean = accepted.mean(axis=0)
        sd = accepted.std(axis=0)
    else:
        mean = np.zeros(n_contestants)
        sd = np.zeros(n_contestants)

    return {
        'accepted_raw': len(accepted_raw),
        'accepted_used': len(accepted),
        'trials': trials,
        'acc_rate': acc_rate,
        'mean': mean,
        'sd': sd,
    }


def main():
    parser = argparse.ArgumentParser(description='ABC batch runner')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--prior', default='data/processed/prior_weekly_alpha.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--log-dir', default='outputs/abc_batch')
    parser.add_argument('--target', type=int, default=500)
    parser.add_argument('--max-trials', type=int, default=200000)
    parser.add_argument('--batch-size', type=int, default=20000)
    parser.add_argument('--single-only', action='store_true')
    parser.add_argument('--season-start', type=int, default=None)
    parser.add_argument('--season-end', type=int, default=None)
    parser.add_argument('--dual-s28', action='store_true')
    parser.add_argument('--pilot-target', type=int, default=200)
    parser.add_argument('--pilot-max-trials', type=int, default=50000)
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    prior = pd.read_csv(args.prior)

    out_dir = Path(args.out_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_dir / f'abc_batch_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    # Filter truth
    truth_work = truth[truth['has_elim']].copy()
    if args.single_only:
        truth_work = truth_work[truth_work['n_elim'] == 1]
    if args.season_start is not None:
        truth_work = truth_work[truth_work['season'] >= args.season_start]
    if args.season_end is not None:
        truth_work = truth_work[truth_work['season'] <= args.season_end]

    rng = np.random.default_rng(123)
    posterior_rows = []
    week_rows = []

    for _, row in truth_work.iterrows():
        season = int(row['season'])
        week = int(row['week'])

        df_week = weekly[(weekly['season'] == season) & (weekly['week'] == week)].copy()
        if df_week.empty:
            continue
        df_week = df_week.set_index('celebrity_name')

        prior_week = prior[(prior['season'] == season) & (prior['week'] == week)].copy()
        if prior_week.empty:
            continue
        prior_week = prior_week.set_index('celebrity_name')

        common = df_week.index.intersection(prior_week.index)
        df_week = df_week.loc[common].copy()
        prior_week = prior_week.loc[common].copy()

        alpha = prior_week['alpha_raw'].values
        n_contestants = len(alpha)

        rule_period = df_week['rule_period'].iloc[0]
        true_set = {name.strip() for name in str(row['elim_names']).split(' | ') if name.strip()}

        if rule_period == 'rank':
            rule = 'rank'
            judges_save = False
        elif rule_period == 'percent':
            rule = 'percent'
            judges_save = False
        else:
            # S28+ default rank+save; optionally dual-hypothesis
            if args.dual_s28:
                pilot_rank = run_abc(
                    alpha, df_week, 'rank', True, true_set,
                    args.pilot_target, args.pilot_max_trials, args.batch_size, rng
                )
                pilot_percent = run_abc(
                    alpha, df_week, 'percent', True, true_set,
                    args.pilot_target, args.pilot_max_trials, args.batch_size, rng
                )
                if pilot_rank['acc_rate'] >= pilot_percent['acc_rate']:
                    rule = 'rank'
                else:
                    rule = 'percent'
            else:
                rule = 'rank'
            judges_save = True

        result = run_abc(
            alpha, df_week, rule, judges_save, true_set,
            args.target, args.max_trials, args.batch_size, rng
        )

        week_rows.append({
            'season': season,
            'week': week,
            'rule_used': rule,
            'judges_save': judges_save,
            'n_contestants': n_contestants,
            'trials': result['trials'],
            'accepted_raw': result['accepted_raw'],
            'accepted_used': result['accepted_used'],
            'acceptance_rate': result['acc_rate'],
            'true_elim': row['elim_names'],
            'n_elim': int(row['n_elim']),
        })

        for name, mean, sd, alpha_raw in zip(df_week.index, result['mean'], result['sd'], alpha):
            posterior_rows.append({
                'season': season,
                'week': week,
                'celebrity_name': name,
                'alpha_raw': float(alpha_raw),
                'posterior_mean': float(mean),
                'posterior_sd': float(sd),
                'rule_used': rule,
                'judges_save': bool(judges_save),
                'acceptance_rate': float(result['acc_rate']),
                'trials': int(result['trials']),
                'accepted_used': int(result['accepted_used']),
            })

    weekly_summary = pd.DataFrame(week_rows)
    weekly_posterior = pd.DataFrame(posterior_rows)

    summary_path = out_dir / 'abc_weekly_summary.csv'
    posterior_path = out_dir / 'abc_weekly_posterior.csv'

    weekly_summary.to_csv(summary_path, index=False)
    weekly_posterior.to_csv(posterior_path, index=False)

    meta = {
        'run_timestamp': run_ts,
        'target': args.target,
        'max_trials': args.max_trials,
        'batch_size': args.batch_size,
        'single_only': bool(args.single_only),
        'season_start': args.season_start,
        'season_end': args.season_end,
        'dual_s28': bool(args.dual_s28),
        'pilot_target': args.pilot_target,
        'pilot_max_trials': args.pilot_max_trials,
        'weekly_summary': str(summary_path),
        'weekly_posterior': str(posterior_path),
        'weeks_run': int(len(weekly_summary)),
    }
    meta_path = log_dir / f'abc_batch_summary_{run_ts}.json'
    meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')

    report_lines = [
        '# ABC Batch Report',
        f'- run_timestamp: {run_ts}',
        f'- target: {args.target}',
        f'- max_trials: {args.max_trials}',
        f'- batch_size: {args.batch_size}',
        f'- single_only: {bool(args.single_only)}',
        f'- season_start: {args.season_start}',
        f'- season_end: {args.season_end}',
        f'- dual_s28: {bool(args.dual_s28)}',
        f'- pilot_target: {args.pilot_target}',
        f'- pilot_max_trials: {args.pilot_max_trials}',
        f'- weeks_run: {int(len(weekly_summary))}',
        f'- weekly_summary: {summary_path}',
        f'- weekly_posterior: {posterior_path}',
    ]
    report_path = log_dir / f'abc_batch_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
