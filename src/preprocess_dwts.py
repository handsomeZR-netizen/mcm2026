import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


def pick_raw_csv(raw_dir: Path):
    csvs = sorted(raw_dir.glob('*.csv'))
    if not csvs:
        raise FileNotFoundError(f'No CSV files found in {raw_dir}')
    if len(csvs) == 1:
        return csvs[0], csvs
    csvs_sorted = sorted(csvs, key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
    return csvs_sorted[0], csvs_sorted


def clean_columns(cols):
    return [str(c).lstrip('\ufeff').strip() for c in cols]


def parse_elim_week(results: str):
    if not isinstance(results, str):
        return None
    m = re.search(r'Eliminated Week\s*(\d+)', results)
    if m:
        return int(m.group(1))
    m = re.search(r'Week\s*(\d+)', results)
    if m and 'Eliminated' in results:
        return int(m.group(1))
    return None


def rule_period(season: int):
    if season <= 2:
        return 'rank'
    if season <= 27:
        return 'percent'
    return 'bottom_two'


def main():
    parser = argparse.ArgumentParser(description='Preprocess DWTS data')
    parser.add_argument('--raw-dir', default='data/raw')
    parser.add_argument('--out-dir', default='data/processed')
    parser.add_argument('--log-dir', default='outputs/preprocess')
    parser.add_argument('--keep-long-all', action='store_true', help='Keep full long table in data/processed')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    log_dir = Path(args.log_dir)
    archive_dir = out_dir / '_archive'
    out_dir.mkdir(parents=True, exist_ok=True)
    if not args.keep_long_all:
        archive_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = log_dir / f'preprocess_{run_ts}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.FileHandler(log_path, encoding='utf-8'), logging.StreamHandler()],
    )

    logging.info('Starting preprocessing')

    raw_path, all_csvs = pick_raw_csv(raw_dir)
    logging.info('Selected raw CSV: %s', raw_path)
    if len(all_csvs) > 1:
        logging.info('Other CSVs found: %s', ', '.join(str(p.name) for p in all_csvs if p != raw_path))

    df = pd.read_csv(raw_path, encoding='utf-8-sig')
    df.columns = clean_columns(df.columns)

    rename_map = {
        'celebrity_homecountry/region': 'celebrity_homecountry_region',
    }
    df = df.rename(columns=rename_map)

    # Base columns
    base_cols = [
        'celebrity_name',
        'ballroom_partner',
        'celebrity_industry',
        'celebrity_homestate',
        'celebrity_homecountry_region',
        'celebrity_age_during_season',
        'season',
        'results',
        'placement',
    ]

    missing_base_cols = [c for c in base_cols if c not in df.columns]
    if missing_base_cols:
        raise KeyError(f'Missing expected columns: {missing_base_cols}')

    # Normalize strings
    string_cols = [
        'celebrity_name',
        'ballroom_partner',
        'celebrity_industry',
        'celebrity_homestate',
        'celebrity_homecountry_region',
        'results',
    ]
    for col in string_cols:
        df[col] = df[col].astype('string').str.strip()
        df[col] = df[col].replace({'': pd.NA, 'NA': pd.NA, 'N/A': pd.NA})

    # Numeric conversions
    df['celebrity_age_during_season'] = pd.to_numeric(df['celebrity_age_during_season'], errors='coerce')
    df['season'] = pd.to_numeric(df['season'], errors='coerce').astype('Int64')
    df['placement'] = pd.to_numeric(df['placement'], errors='coerce').astype('Int64')

    # Judge score columns
    judge_pattern = re.compile(r'^week(\d+)_judge(\d+)_score$')
    judge_cols = [c for c in df.columns if judge_pattern.match(c)]
    if not judge_cols:
        raise KeyError('No week/judge score columns found')

    df[judge_cols] = df[judge_cols].replace({'N/A': pd.NA, 'NA': pd.NA, '': pd.NA})
    df[judge_cols] = df[judge_cols].apply(pd.to_numeric, errors='coerce')

    # Homestate missing flag
    df['homestate_missing'] = df['celebrity_homestate'].isna()
    df['celebrity_homestate'] = df['celebrity_homestate'].fillna('Unknown')

    # Basic stats for logging
    seasons = sorted(df['season'].dropna().unique().tolist())
    week_nums = sorted({int(judge_pattern.match(c).group(1)) for c in judge_cols})
    judge_ids = sorted({int(judge_pattern.match(c).group(2)) for c in judge_cols})

    logging.info('Rows: %s | Cols: %s', len(df), len(df.columns))
    logging.info('Seasons: %s-%s (%s total)', seasons[0], seasons[-1], len(seasons))
    logging.info('Week range: %s-%s | Judge IDs: %s', min(week_nums), max(week_nums), judge_ids)

    # Week existence per season
    season_week_exists = {s: {} for s in seasons}
    for s in seasons:
        sdf = df[df['season'] == s]
        for w in week_nums:
            wcols = [c for c in judge_cols if c.startswith(f'week{w}_')]
            exists = sdf[wcols].notna().sum().sum() > 0
            season_week_exists[s][w] = bool(exists)

    # Last week per season
    season_last_week = {
        s: max([w for w, exists in season_week_exists[s].items() if exists], default=max(week_nums))
        for s in seasons
    }

    # Precompute week columns map for per-row inference
    week_cols_map = {w: [c for c in judge_cols if c.startswith(f'week{w}_')] for w in week_nums}

    # Parse elimination week from results
    unparsed_results = []
    elim_week_results = []
    for _, row in df.iterrows():
        res = row['results']
        ew = parse_elim_week(res)
        if ew is None and isinstance(res, str) and ('Place' in res or 'Final' in res):
            ew = season_last_week[int(row['season'])]
        if ew is None:
            unparsed_results.append(res)
        elim_week_results.append(ew)

    df['elim_week_results'] = elim_week_results

    # Infer elimination week from scores (last week with any score > 0)
    score_df = df[judge_cols].astype(float)
    elim_week_scores = pd.Series(pd.NA, index=df.index, dtype='Int64')
    for w in sorted(week_nums, reverse=True):
        wcols = week_cols_map[w]
        has_score = (score_df[wcols].fillna(0) > 0).any(axis=1)
        assign_mask = has_score & elim_week_scores.isna()
        elim_week_scores.loc[assign_mask] = w
    df['elim_week_scores'] = elim_week_scores

    # Final elimination week: prefer results, fallback to score inference, then season last week
    df['elim_week'] = df['elim_week_results']
    df.loc[df['elim_week'].isna(), 'elim_week'] = df.loc[df['elim_week'].isna(), 'elim_week_scores']
    df['season_last_week'] = df['season'].map(season_last_week)
    df.loc[df['elim_week'].isna(), 'elim_week'] = df.loc[df['elim_week'].isna(), 'season_last_week']
    df['rule_period'] = df['season'].map(lambda s: rule_period(int(s)))

    # Mismatch check between results and score inference
    mismatch_mask = df['elim_week_results'].notna() & df['elim_week_scores'].notna() & (df['elim_week_results'] != df['elim_week_scores'])
    mismatch_count = int(mismatch_mask.sum())
    infer_used_mask = df['elim_week_results'].isna() & df['elim_week_scores'].notna()
    infer_used_count = int(infer_used_mask.sum())

    # Score range check
    score_stack = df[judge_cols].stack(future_stack=True)
    out_of_range = ((score_stack < 0) | (score_stack > 10)).sum()

    # QA tables
    mismatch_path = log_dir / f'elim_week_mismatch_{run_ts}.csv'
    infer_used_path = log_dir / f'elim_week_infer_used_{run_ts}.csv'
    if mismatch_count > 0:
        df.loc[mismatch_mask, ['celebrity_name', 'season', 'results', 'elim_week_results', 'elim_week_scores', 'elim_week']].to_csv(
            mismatch_path, index=False
        )
    if infer_used_count > 0:
        df.loc[infer_used_mask, ['celebrity_name', 'season', 'results', 'elim_week_scores', 'elim_week']].to_csv(
            infer_used_path, index=False
        )

    # Out-of-range score details
    oor_records = []
    for col in judge_cols:
        m = judge_pattern.match(col)
        if not m:
            continue
        week = int(m.group(1))
        judge_id = int(m.group(2))
        bad_mask = df[col].notna() & ((df[col] < 0) | (df[col] > 10))
        if bad_mask.any():
            sub = df.loc[bad_mask, ['celebrity_name', 'season', col]]
            for idx, row in sub.iterrows():
                oor_records.append({
                    'celebrity_name': row['celebrity_name'],
                    'season': int(row['season']) if pd.notna(row['season']) else pd.NA,
                    'week': week,
                    'judge_id': judge_id,
                    'score': row[col],
                })
    out_of_range_path = log_dir / f'out_of_range_scores_{run_ts}.csv'
    if oor_records:
        pd.DataFrame(oor_records).to_csv(out_of_range_path, index=False)

    # Save cleaned wide
    wide_path = out_dir / 'dwts_wide_clean.csv'
    df.to_csv(wide_path, index=False)

    # Build long format
    long_frames = []
    for w in week_nums:
        wcols = [c for c in judge_cols if c.startswith(f'week{w}_')]
        tmp_cols = base_cols + ['homestate_missing', 'elim_week', 'season_last_week', 'rule_period'] + wcols
        tmp = df[tmp_cols].copy()
        tmp['week'] = w
        # Rename week-specific judge columns to judgeX_score
        rename_week = {}
        for c in wcols:
            m = judge_pattern.match(c)
            if not m:
                continue
            j_id = int(m.group(2))
            rename_week[c] = f'judge{j_id}_score'
        tmp = tmp.rename(columns=rename_week)
        judge_cols_week = [rename_week[c] for c in wcols]
        tmp['num_judges_scored'] = tmp[judge_cols_week].notna().sum(axis=1)
        tmp['judge_total'] = tmp[judge_cols_week].sum(axis=1, skipna=True)
        tmp['judge_mean'] = tmp['judge_total'] / tmp['num_judges_scored']
        tmp.loc[tmp['num_judges_scored'] == 0, ['judge_total', 'judge_mean']] = pd.NA
        tmp['week_exists'] = tmp['season'].map(lambda s: season_week_exists[int(s)][w])
        tmp['active_in_week'] = tmp['week_exists'] & (tmp['week'] <= tmp['elim_week'])
        long_frames.append(tmp)

    long_df = pd.concat(long_frames, ignore_index=True)

    # Add judge_pct and judge_rank within each season-week (active only)
    long_df['judge_pct'] = pd.NA
    long_df['judge_rank'] = pd.NA

    active_mask = long_df['active_in_week'] & long_df['judge_total'].notna()
    group_sum = (
        long_df['judge_total']
        .where(active_mask)
        .groupby([long_df['season'], long_df['week']])
        .transform('sum')
    )
    pct_mask = active_mask & (group_sum > 0)
    long_df.loc[pct_mask, 'judge_pct'] = long_df.loc[pct_mask, 'judge_total'] / group_sum[pct_mask]

    long_df.loc[active_mask, 'judge_rank'] = (
        long_df.loc[active_mask]
        .groupby(['season', 'week'])['judge_total']
        .rank(method='min', ascending=False)
        .astype('Int64')
    )

    # Active-only long data
    long_active = long_df[long_df['active_in_week']].copy()

    long_all_path = out_dir / 'dwts_weekly_long_all.csv'
    if not args.keep_long_all:
        long_all_path = archive_dir / 'dwts_weekly_long_all.csv'
    long_active_path = out_dir / 'dwts_weekly_long.csv'
    long_df.to_csv(long_all_path, index=False)
    long_active.to_csv(long_active_path, index=False)

    # Season-week summary
    summary = (
        long_active.groupby(['season', 'week'], as_index=False)
        .agg(
            n_active=('celebrity_name', 'count'),
            judge_total_sum=('judge_total', 'sum'),
            judge_total_mean=('judge_total', 'mean'),
            judge_total_min=('judge_total', 'min'),
            judge_total_max=('judge_total', 'max'),
        )
    )
    summary_path = out_dir / 'season_week_summary.csv'
    summary.to_csv(summary_path, index=False)

    # Season info
    season_info = pd.DataFrame({
        'season': seasons,
        'season_last_week': [season_last_week[s] for s in seasons],
    })
    season_info_path = out_dir / 'season_info.csv'
    season_info.to_csv(season_info_path, index=False)

    # Write run summary JSON
    summary_json = {
        'run_timestamp': run_ts,
        'raw_csv': str(raw_path),
        'rows': int(len(df)),
        'cols': int(len(df.columns)),
        'seasons': {'min': int(seasons[0]), 'max': int(seasons[-1]), 'n_unique': int(len(seasons))},
        'weeks': {'min': int(min(week_nums)), 'max': int(max(week_nums)), 'n_unique': int(len(week_nums))},
        'judge_ids': judge_ids,
        'missing_homestate': int(df['homestate_missing'].sum()),
        'out_of_range_scores': int(out_of_range),
        'elim_week_infer_used': int(infer_used_count),
        'elim_week_result_score_mismatch': int(mismatch_count),
        'unparsed_results': sorted(set(r for r in unparsed_results if r is not None)),
        'decisions': {
            'score_out_of_range_handling': 'kept_raw',
            'score_out_of_range_threshold': {'min': 0, 'max': 10},
            'elim_week_priority': 'results_then_scores_then_season_last_week',
            'keep_long_all_in_processed': bool(args.keep_long_all),
        },
        'qa_files': {
            'elim_week_mismatch': str(mismatch_path) if mismatch_count > 0 else None,
            'elim_week_infer_used': str(infer_used_path) if infer_used_count > 0 else None,
            'out_of_range_scores': str(out_of_range_path) if int(out_of_range) > 0 else None,
        },
        'outputs': {
            'wide_clean': str(wide_path),
            'long_all': str(long_all_path),
            'long_active': str(long_active_path),
            'season_week_summary': str(summary_path),
            'season_info': str(season_info_path),
        },
    }
    summary_json_path = log_dir / f'preprocess_summary_{run_ts}.json'
    summary_json_path.write_text(json.dumps(summary_json, indent=2), encoding='utf-8')

    # Human-readable report
    report_lines = [
        '# Preprocess Report',
        f'- run_timestamp: {run_ts}',
        f'- raw_csv: {raw_path}',
        f'- rows: {len(df)}',
        f'- cols: {len(df.columns)}',
        f'- seasons: {seasons[0]}-{seasons[-1]} (n={len(seasons)})',
        f'- weeks: {min(week_nums)}-{max(week_nums)} (n={len(week_nums)})',
        f'- judge_ids: {judge_ids}',
        f'- missing_homestate: {int(df["homestate_missing"].sum())}',
        f'- out_of_range_scores: {int(out_of_range)}',
        f'- elim_week_infer_used: {int(infer_used_count)}',
        f'- elim_week_result_score_mismatch: {int(mismatch_count)}',
        f'- unparsed_results: {sorted(set(r for r in unparsed_results if r is not None))}',
        '- decision_score_out_of_range_handling: kept_raw',
        '- decision_elim_week_priority: results_then_scores_then_season_last_week',
        f'- decision_keep_long_all_in_processed: {bool(args.keep_long_all)}',
        f'- qa_elim_week_mismatch: {mismatch_path if mismatch_count > 0 else "None"}',
        f'- qa_elim_week_infer_used: {infer_used_path if infer_used_count > 0 else "None"}',
        f'- qa_out_of_range_scores: {out_of_range_path if int(out_of_range) > 0 else "None"}',
        '',
        '## Outputs',
        f'- {wide_path}',
        f'- {long_all_path}',
        f'- {long_active_path}',
        f'- {summary_path}',
        f'- {season_info_path}',
    ]
    report_path = log_dir / f'preprocess_report_{run_ts}.md'
    report_path.write_text('\n'.join(report_lines), encoding='utf-8')

    logging.info('Preprocessing complete')
    logging.info('Report: %s', report_path)
    logging.info('Summary JSON: %s', summary_json_path)


if __name__ == '__main__':
    main()
