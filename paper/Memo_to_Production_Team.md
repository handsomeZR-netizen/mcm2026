# MEMORANDUM

**TO**: DWTS Executive Producers  
**FROM**: Modeling Team  
**DATE**: February 1, 2026  
**RE**: A transparent voting rule that preserves heat early and protects technical winners late

---

## Executive Summary (One Paragraph)

DWTS’s outcomes are driven by two forces: **judges’ technical scores** and **fan voting** (hidden). Our modeling shows fan voting is the dominant “survival” driver (Cox model: mean fan share HR≈0.227 vs. mean judge score HR≈0.525), which explains why highly polarizing seasons can produce controversial finales. We recommend a **simple, transparent rule**—**Adaptive Percent + Mix Save**—that keeps early-week volatility (engagement) while reducing late-stage “pure popularity wins” that trigger backlash.

---

## What’s Actually Causing Controversy

- **Percent-style aggregation preserves magnitude**: extreme fan mobilization can dominate outcomes even when judges’ scores are strong.
- **Rank-style aggregation compresses magnitude**: it protects technical leaders but risks the perception that “votes don’t matter.”
- **Result**: controversy is not random; it’s a predictable consequence of which rule is emphasized *when*.

---

## The Recommendation: Adaptive Percent + Mix Save

**Core message for viewers**: “Your votes matter most early; champions must prove skills late.”

Rule (minimal form):
- Compute weekly `judge_pct` and `fan_pct`.
- Use a **small, linear weight shift**: judge weight $w_t$ increases from **0.45 → 0.55** across the season.
- Score: `score = w_t * judge_pct + (1 - w_t) * fan_pct`.
- Keep the existing **Bottom Two + Save** mechanism, using the **Mix** strategy (merit when separation is clear; fan-leaning when it’s a coin flip).

Why producers should care:
- **Keeps the early-season “shock” potential** that drives conversation.
- **Reduces finale-stage betrayal risk** (“pure popularity stole the trophy”), the PR pain point highlighted by Season 27.
- **Makes the rule explainable on-air** (a visible weight bar each week).

---

## How to Roll Out Without Killing Heat

- **On-air transparency**: show the week’s split (e.g., “This week: Fans 52% / Judges 48%”).
- **Producer KPI dashboard** (weekly): FII / TPI / Consistency as operational tracking (engagement proxy / technical protection / historical alignment).
- **Post-season review**: adjust only the *range* ($w_{\min}, w_{\max}$), keep the concept unchanged.

---

## Risk Notes (and Simple Mitigations)

- **“You took away our power” backlash**: emphasize fans still lead early; only the finale tilts slightly toward merit.
- **Complexity perception**: keep the range narrow (0.45–0.55) and the curve linear; communicate one rule, not many.
- **Controversy won’t disappear**: reframe it as a *transparent design tradeoff*, not a black box.
