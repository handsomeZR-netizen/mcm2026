import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd


def classify_result(result: str) -> str:
    if pd.isna(result):
        return 'unknown'
    text = str(result)
    if 'Eliminated' in text:
        return 'eliminated'
    if 'Withdrew' in text:
        return 'withdrew'
    if 'Place' in text:
        return 'finalist'
    return 'other'


def main():
    parser = argparse.ArgumentParser(description='Build season-week elimination truth table')
    parser.add_argument('--input', default='data/processed/dwts_weekly_long.csv')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--log-dir', default='outputs/groundtruth')
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    log_dir = Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = log_dir / f'groundtruth_{run_ts}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler()],
    )

    logging.info('Starting groundtruth build')
    df = pd.read_csv(input_path)

    required = {
        'celebrity_name', 'season', 'week', 'results', 'elim_week', 'season_last_week', 'rule_period'
    }
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f'Missing required columns: {sorted(missing)}')

    df['result_class'] = df['results'].apply(classify_result)
    df['elim_event'] = (df['elim_week'] == df['week']) & df['result_class'].isin(['eliminated', 'withdrew'])

    def summarize(group: pd.DataFrame) -> pd.Series:
        season, week = group.name
        elim = group[group['elim_event']]
        n_elim = len(elim)
        if n_elim == 0:
            elim_type = 'none'
        else:
            classes = set(elim['result_class'].tolist())
            if classes == {'eliminated'}:
                elim_type = 'eliminated'
            elif classes == {'withdrew'}:
                elim_type = 'withdrew'
            else:
                elim_type = 'mixed'
        return pd.Series({
            'season': int(season),
            'week': int(week),
            'rule_period': group['rule_period'].iloc[0],
            'season_last_week': int(group['season_last_week'].iloc[0]),
            'n_active': int(len(group)),
            'n_elim': int(n_elim),
            'elim_names': ' | '.join(elim['celebrity_name'].tolist()) if n_elim else '',
            'elim_results': ' | '.join(elim['results'].tolist()) if n_elim else '',
            'elim_type': elim_type,
            'has_elim': bool(n_elim > 0),
            'final_week': bool(int(week) == int(group['season_last_week'].iloc[0])),
        })

    truth = df.groupby(['season', 'week']).apply(summarize, include_groups=False).reset_index(drop=True)

    out_path = out_dir / 'season_week_truth.csv'
    truth.to_csv(out_path, index=False)

    # Summary stats
    total_weeks = len(truth)
    weeks_with_elim = int(truth['has_elim'].sum())
    weeks_no_elim = int((~truth['has_elim']).sum())
    multi_elim = int((truth['n_elim'] > 1).sum())
    withdrew_weeks = int((truth['elim_type'] == 'withdrew').sum())
    mixed_weeks = int((truth['elim_type'] == 'mixed').sum())

    summary = {
        'run_timestamp': run_ts,
        'input': str(input_path),
        'output': str(out_path),
        'total_season_weeks': total_weeks,
        'weeks_with_elimination': weeks_with_elim,
        'weeks_without_elimination': weeks_no_elim,
        'weeks_with_multiple_eliminations': multi_elim,
        'weeks_with_withdrawal_only': withdrew_weeks,
        'weeks_with_mixed_elimination': mixed_weeks,
    }
    summary_path = log_dir / f'groundtruth_summary_{run_ts}.json'
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    report_lines = [
        '# Groundtruth Build Report',
        f'- run_timestamp: {run_ts}',
        f'- input: {input_path}',
        f'- output: {out_path}',
        f'- total_season_weeks: {total_weeks}',
        f'- weeks_with_elimination: {weeks_with_elim}',
        f'- weeks_without_elimination: {weeks_no_elim}',
        f'- weeks_with_multiple_eliminations: {multi_elim}',
        f'- weeks_with_withdrawal_only: {withdrew_weeks}',
        f'- weeks_with_mixed_elimination: {mixed_weeks}',
    ]
    report_path = log_dir / f'groundtruth_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Groundtruth build complete')
    logging.info('Report: %s', report_path)
    logging.info('Summary: %s', summary_path)


if __name__ == '__main__':
    main()
