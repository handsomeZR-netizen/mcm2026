import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description='ABC single-week pilot (vectorized)')
    parser.add_argument('--weekly', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--prior', default='data/processed/prior_weekly_alpha.csv')
    parser.add_argument('--season', type=int, default=None)
    parser.add_argument('--week', type=int, default=None)
    parser.add_argument('--target', type=int, default=2000)
    parser.add_argument('--max-trials', type=int, default=1000000)
    parser.add_argument('--rule', choices=['rank', 'percent'], default=None)
    parser.add_argument('--judges-save', action='store_true')
    parser.add_argument('--batch-size', type=int, default=20000)
    parser.add_argument('--log-dir', default='outputs/abc')
    args = parser.parse_args()

    weekly = pd.read_csv(args.weekly)
    truth = pd.read_csv(args.truth)
    prior = pd.read_csv(args.prior)

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_dir / f'abc_{run_ts}.log', encoding='utf-8'), logging.StreamHandler()],
    )

    # Auto-select season/week if not provided
    if args.season is None or args.week is None:
        truth_work = truth[truth['has_elim'] & (truth['n_elim'] == 1)].copy()
        if truth_work.empty:
            raise ValueError('No single-elimination weeks found for auto-selection')
        # season_week_truth already contains n_active from Step1
        truth_work = truth_work.sort_values(['n_active', 'season', 'week'], ascending=[True, False, False])
        pick = truth_work.iloc[0]
        args.season = int(pick['season'])
        args.week = int(pick['week'])
        logging.info('Auto-selected season/week: S%s W%s (n_active=%s)', args.season, args.week, int(pick['n_active']))

    # Subset week
    df_week = weekly[(weekly['season'] == args.season) & (weekly['week'] == args.week)].copy()
    if df_week.empty:
        raise ValueError('No rows for season/week')

    # True elimination
    truth_row = truth[(truth['season'] == args.season) & (truth['week'] == args.week)]
    if truth_row.empty:
        raise ValueError('No truth row for season/week')
    truth_row = truth_row.iloc[0]
    true_elim = truth_row['elim_names']
    n_elim = int(truth_row['n_elim'])

    # Rule selection
    rule = args.rule
    judges_save = args.judges_save
    if rule is None:
        if df_week['rule_period'].iloc[0] == 'rank':
            rule = 'rank'
        elif df_week['rule_period'].iloc[0] == 'percent':
            rule = 'percent'
        else:
            rule = 'rank'
            judges_save = True

    # Prior alpha
    prior_week = prior[(prior['season'] == args.season) & (prior['week'] == args.week)]
    if prior_week.empty:
        raise ValueError('No prior rows for season/week')
    prior_week = prior_week.set_index('celebrity_name')

    # Align order
    df_week = df_week.set_index('celebrity_name')
    common = df_week.index.intersection(prior_week.index)
    df_week = df_week.loc[common].copy()
    prior_week = prior_week.loc[common].copy()

    alpha = prior_week['alpha_raw'].values
    alpha = np.clip(alpha, 1e-6, None)
    n_contestants = len(alpha)

    # Precompute judge terms
    judge_total = df_week['judge_total'].values.astype(float)
    if rule == 'rank':
        judge_rank = pd.Series(judge_total).rank(method='min', ascending=False).values
    else:
        total = judge_total.sum()
        judge_pct = judge_total / total if total > 0 else np.zeros_like(judge_total)

    true_set = {name.strip() for name in str(true_elim).split(' | ') if name.strip()}

    rng = np.random.default_rng(123)
    accepted_chunks = []
    trials = 0

    while sum(len(x) for x in accepted_chunks) < args.target and trials < args.max_trials:
        batch = min(args.batch_size, args.max_trials - trials)
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

    if len(accepted_raw) > args.target:
        accepted = accepted_raw[: args.target]
    else:
        accepted = accepted_raw

    if len(accepted) > 0:
        mean = accepted.mean(axis=0)
        sd = accepted.std(axis=0)
    else:
        mean = np.zeros(len(alpha))
        sd = np.zeros(len(alpha))

    post_path = log_dir / f'abc_posterior_{args.season}_{args.week}_{run_ts}.csv'
    summary_path = log_dir / f'abc_summary_{args.season}_{args.week}_{run_ts}.json'
    report_path = log_dir / f'abc_report_{args.season}_{args.week}_{run_ts}.md'

    post_df = pd.DataFrame({
        'celebrity_name': df_week.index,
        'alpha_raw': alpha,
        'posterior_mean': mean,
        'posterior_sd': sd,
    })
    post_df.to_csv(post_path, index=False)

    summary = {
        'run_timestamp': run_ts,
        'season': args.season,
        'week': args.week,
        'rule': rule,
        'judges_save': bool(judges_save),
        'target_samples': args.target,
        'max_trials': args.max_trials,
        'trials': trials,
        'accepted_raw': int(len(accepted_raw)),
        'accepted_used': int(len(accepted)),
        'acceptance_rate': acc_rate,
        'true_elim': true_elim,
        'n_elim': n_elim,
        'n_contestants': int(n_contestants),
        'batch_size': int(args.batch_size),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# ABC Pilot Report',
        f'- run_timestamp: {run_ts}',
        f'- season: {args.season}',
        f'- week: {args.week}',
        f'- rule: {rule}',
        f'- judges_save: {bool(judges_save)}',
        f'- true_elim: {true_elim}',
        f'- n_elim: {n_elim}',
        f'- n_contestants: {int(n_contestants)}',
        f'- batch_size: {int(args.batch_size)}',
        f'- target_samples: {args.target}',
        f'- max_trials: {args.max_trials}',
        f'- trials: {trials}',
        f'- accepted_raw: {len(accepted_raw)}',
        f'- accepted_used: {len(accepted)}',
        f'- acceptance_rate: {acc_rate:.6f}',
        f'- posterior_path: {post_path}',
    ]
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
