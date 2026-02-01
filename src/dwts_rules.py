"""DWTS rule engine utilities.

These functions apply the show rules to a single season-week dataframe and
return eliminated contestants or bottom-two candidates.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


def _as_series(values: Iterable[float], index) -> pd.Series:
    series = pd.Series(list(values), index=index, dtype='float64')
    return series


def compute_judge_rank(judge_total: pd.Series) -> pd.Series:
    """Rank judges' total scores (1 = highest).

    Ties use the minimum rank to match contest ranking behavior.
    """
    return judge_total.rank(method='min', ascending=False)


def compute_judge_pct(judge_total: pd.Series) -> pd.Series:
    """Compute judge percentage share for the week."""
    total = judge_total.sum()
    if total == 0:
        return judge_total * 0
    return judge_total / total


def compute_fan_rank(fan_votes: pd.Series) -> pd.Series:
    """Rank fan votes (1 = highest votes)."""
    return fan_votes.rank(method='min', ascending=False)


def compute_fan_pct(fan_votes: pd.Series) -> pd.Series:
    """Compute fan percentage share for the week."""
    total = fan_votes.sum()
    if total == 0:
        return fan_votes * 0
    return fan_votes / total


def _tie_break_sort(df: pd.DataFrame, combined: pd.Series, fan_votes: pd.Series, worse_is_higher: bool) -> pd.DataFrame:
    """Sort rows by combined score plus tie-breakers.

    worse_is_higher=True for Rank rule (higher combined is worse).
    worse_is_higher=False for Percent rule (lower combined is worse).
    """
    tmp = df.copy()
    tmp['_combined'] = combined.values
    tmp['_fan_votes'] = fan_votes.values
    tmp['_judge_total'] = df['judge_total'].values
    # Sort: primary combined, then fan_votes (lower is worse), then judge_total (lower is worse)
    tmp = tmp.sort_values(
        by=['_combined', '_fan_votes', '_judge_total', 'celebrity_name'],
        ascending=[not worse_is_higher, True, True, True],
        kind='mergesort',
    )
    return tmp


def apply_rank_rule(df_week: pd.DataFrame, fan_votes: Iterable[float]) -> Tuple[str, pd.DataFrame]:
    """Apply Rank-Sum rule and return eliminated name and ranked table."""
    if 'judge_total' not in df_week.columns:
        raise KeyError('judge_total is required')

    fan_votes = _as_series(fan_votes, df_week.index)
    judge_rank = compute_judge_rank(df_week['judge_total'])
    fan_rank = compute_fan_rank(fan_votes)
    combined = judge_rank + fan_rank

    ordered = _tie_break_sort(df_week, combined, fan_votes, worse_is_higher=True)
    eliminated = ordered.iloc[0]['celebrity_name']

    ordered = ordered.assign(
        judge_rank=judge_rank.values,
        fan_rank=fan_rank.values,
        combined_rank=combined.values,
    )
    return eliminated, ordered


def apply_percent_rule(df_week: pd.DataFrame, fan_votes: Iterable[float]) -> Tuple[str, pd.DataFrame]:
    """Apply Percent-Sum rule and return eliminated name and ranked table."""
    if 'judge_total' not in df_week.columns:
        raise KeyError('judge_total is required')

    fan_votes = _as_series(fan_votes, df_week.index)
    judge_pct = compute_judge_pct(df_week['judge_total'])
    fan_pct = compute_fan_pct(fan_votes)
    combined = 0.5 * judge_pct + 0.5 * fan_pct

    ordered = _tie_break_sort(df_week, combined, fan_votes, worse_is_higher=False)
    eliminated = ordered.iloc[0]['celebrity_name']

    ordered = ordered.assign(
        judge_pct=judge_pct.values,
        fan_pct=fan_pct.values,
        combined_pct=combined.values,
    )
    return eliminated, ordered


def apply_adaptive_percent_rule(
    df_week: pd.DataFrame,
    fan_votes: Iterable[float],
    weight: float,
) -> Tuple[str, pd.DataFrame]:
    """Apply adaptive percent rule with a given judge weight.

    weight in [0,1] controls the judge share. fan share uses (1-weight).
    """
    if 'judge_total' not in df_week.columns:
        raise KeyError('judge_total is required')

    fan_votes = _as_series(fan_votes, df_week.index)
    judge_pct = compute_judge_pct(df_week['judge_total'])
    fan_pct = compute_fan_pct(fan_votes)
    w = float(weight)
    combined = w * judge_pct + (1.0 - w) * fan_pct

    ordered = _tie_break_sort(df_week, combined, fan_votes, worse_is_higher=False)
    eliminated = ordered.iloc[0]['celebrity_name']

    ordered = ordered.assign(
        judge_pct=judge_pct.values,
        fan_pct=fan_pct.values,
        combined_pct=combined.values,
        judge_weight=w,
    )
    return eliminated, ordered


def bottom_two(
    df_week: pd.DataFrame,
    fan_votes: Iterable[float],
    rule: str,
    weight: float | None = None,
) -> Tuple[List[str], pd.DataFrame]:
    """Return bottom two candidates under a given rule (rank/percent/adaptive_percent)."""
    rule = rule.lower()
    if rule not in {'rank', 'percent', 'adaptive_percent'}:
        raise ValueError('rule must be rank, percent, or adaptive_percent')

    if rule == 'rank':
        eliminated, ordered = apply_rank_rule(df_week, fan_votes)
        # Ordered worst -> best; take first two
        bottom = ordered.iloc[:2]['celebrity_name'].tolist()
        return bottom, ordered

    if rule == 'adaptive_percent':
        if weight is None:
            raise ValueError('adaptive_percent requires weight')
        eliminated, ordered = apply_adaptive_percent_rule(df_week, fan_votes, weight)
        bottom = ordered.iloc[:2]['celebrity_name'].tolist()
        return bottom, ordered

    eliminated, ordered = apply_percent_rule(df_week, fan_votes)
    bottom = ordered.iloc[:2]['celebrity_name'].tolist()
    return bottom, ordered


def apply_rule(
    df_week: pd.DataFrame,
    fan_votes: Iterable[float],
    rule: str,
    judges_save: bool = False,
    weight: float | None = None,
) -> Dict[str, object]:
    """Apply rule and return result dict.

    If judges_save is True, return bottom_two set and do not assert the final elimination.
    """
    if judges_save:
        bottom, ordered = bottom_two(df_week, fan_votes, rule, weight=weight)
        return {'bottom_two': bottom, 'ordered': ordered}

    if rule == 'rank':
        eliminated, ordered = apply_rank_rule(df_week, fan_votes)
    elif rule == 'percent':
        eliminated, ordered = apply_percent_rule(df_week, fan_votes)
    elif rule == 'adaptive_percent':
        if weight is None:
            raise ValueError('adaptive_percent requires weight')
        eliminated, ordered = apply_adaptive_percent_rule(df_week, fan_votes, weight)
    else:
        raise ValueError('rule must be rank, percent, or adaptive_percent')

    return {'eliminated': eliminated, 'ordered': ordered}
