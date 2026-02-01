import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from dwts_rules import apply_rule


def main():
    parser = argparse.ArgumentParser(description='Rule engine smoketest')
    parser.add_argument('--input', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--truth', default='data/processed/season_week_truth.csv')
    parser.add_argument('--log-dir', default='outputs/rules')
    args = parser.parse_args()

    input_path = Path(args.input)
    truth_path = Path(args.truth)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    df = pd.read_csv(input_path)
    truth = pd.read_csv(truth_path)

    # Simple proxy fan votes: shift judge_total to positive and add tiny noise for stability
    proxy_votes = df['judge_total'].fillna(0) - df['judge_total'].min() + 1.0
    rng = np.random.default_rng(42)
    proxy_votes = proxy_votes + rng.normal(0, 1e-6, size=len(proxy_votes))
    df = df.assign(_proxy_votes=proxy_votes)

    results = []
    for (season, week), grp in df.groupby(['season', 'week']):
        grp = grp.reset_index(drop=True)
        fan_votes = grp['_proxy_votes'].values

        # Rule period decides default rule
        rule_period = grp['rule_period'].iloc[0]
        if rule_period == 'rank':
            rule = 'rank'
            judges_save = False
        elif rule_period == 'percent':
            rule = 'percent'
            judges_save = False
        else:
            rule = 'rank'
            judges_save = True

        output = apply_rule(grp, fan_votes, rule=rule, judges_save=judges_save)

        if judges_save:
            predicted = ' | '.join(output['bottom_two'])
        else:
            predicted = output['eliminated']

        results.append({
            'season': int(season),
            'week': int(week),
            'rule_period': rule_period,
            'rule_used': rule,
            'judges_save': bool(judges_save),
            'predicted': predicted,
        })

    pred_df = pd.DataFrame(results)
    merged = pred_df.merge(truth, on=['season', 'week'], how='left')

    # Evaluate only weeks with single elimination events
    eval_df = merged[merged['has_elim'] & (merged['n_elim'] == 1)].copy()
    def hit(row):
        if row['judges_save']:
            # For bottom-two weeks, success if true elim appears in predicted bottom two
            return row['elim_names'] in row['predicted']
        return row['elim_names'] == row['predicted']

    eval_df['match'] = eval_df.apply(hit, axis=1)
    accuracy = float(eval_df['match'].mean()) if len(eval_df) else 0.0
    total_elim_weeks = int(merged['has_elim'].sum())
    single_elim_weeks = int((merged['has_elim'] & (merged['n_elim'] == 1)).sum())
    multi_elim_weeks = int((merged['n_elim'] > 1).sum())

    summary = {
        'run_timestamp': run_ts,
        'input': str(input_path),
        'truth': str(truth_path),
        'proxy_votes': 'shifted_judge_total_plus_noise',
        'evaluated_weeks': int(len(eval_df)),
        'total_elimination_weeks': total_elim_weeks,
        'single_elimination_weeks': single_elim_weeks,
        'multi_elimination_weeks': multi_elim_weeks,
        'match_rate': accuracy,
    }

    report_lines = [
        '# Rule Engine Smoketest',
        f'- run_timestamp: {run_ts}',
        f'- input: {input_path}',
        f'- truth: {truth_path}',
        f'- proxy_votes: shifted_judge_total_plus_noise',
        f'- evaluated_weeks: {int(len(eval_df))}',
        f'- total_elimination_weeks: {total_elim_weeks}',
        f'- single_elimination_weeks: {single_elim_weeks}',
        f'- multi_elimination_weeks: {multi_elim_weeks}',
        f'- match_rate: {accuracy:.4f}',
    ]

    report_path = log_dir / f'rule_engine_report_{run_ts}.md'
    summary_path = log_dir / f'rule_engine_summary_{run_ts}.json'
    pred_path = log_dir / f'rule_engine_predictions_{run_ts}.csv'

    report_path.write_text('\n'.join(report_lines), encoding='utf-8')
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    pred_df.to_csv(pred_path, index=False)


if __name__ == '__main__':
    main()
