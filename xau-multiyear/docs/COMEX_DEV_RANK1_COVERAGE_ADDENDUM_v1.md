# COMEX DEV_RANK1 — Corrected coverage feasibility addendum v1

Date: 2026-08-18
Status: frozen pre-acquisition.

This addendum supersedes all earlier DEV_RANK1 coverage summaries that used the incorrect helper `date(ts - 17h)`. The canonical XAU research-day key is the existing engine rule: New York local calendar date, advanced by one day when local hour >= 17:00 (vectorized equivalent: `date(local_time + 7h)`). Session selection itself is unchanged.

## Corrected inventory

Selected DEV_RANK1 sessions: **96**.
Sessions containing one or more canonical XAU events: **96**.
Canonical events on those sessions: **31,710** across 2011–2018.

Broad-family inventory:

- FVG_ONLY: 29,797 events / 96 sessions / 8 years;
- OBJECTIVE_ONLY: 704 / 96 / 8;
- CONFLUENCE: 655 / 96 / 8;
- DOZ_ONLY: 426 / 90 / 8;
- MEMORY_ONLY: 128 / 38 / 8.

Acquisition keeps all raw observations, but family-specific modeling remains mandatory and FVG may not dominate a pooled model by raw row count.

## Entry-model feasibility flags

### ACCEPTANCE_RETEST

- CONFLUENCE: 28 events / 23 independent sessions / 7 years;
- DOZ_ONLY: 5 / 5 / 4;
- FVG_ONLY: 156 / 69 / 8;
- MEMORY_ONLY: 4 / 3 / 3;
- OBJECTIVE_ONLY: 14 / 12 / 6.

**Primary interpretation:** ACCEPTANCE_RETEST is exploratory/inconclusive at family level in DEV_RANK1, except that FVG provides enough observations for descriptive feature discovery but not final validation. No non-FVG ACCEPTANCE_RETEST cell may be promoted or rejected from DEV_RANK1 alone.

### FAILED_AUCTION

- CONFLUENCE: 307 / 90 / 8;
- DOZ_ONLY: 64 / 46 / 8;
- FVG_ONLY: 14,027 / 95 / 8;
- MEMORY_ONLY: 16 / 6 / 5;
- OBJECTIVE_ONLY: 73 / 42 / 8.

MEMORY_ONLY × FAILED_AUCTION is explicitly `INCONCLUSIVE` for inferential claims.

### CLEAN_REJECTION

- CONFLUENCE: 273 / 88 / 8;
- DOZ_ONLY: 344 / 88 / 8;
- FVG_ONLY: 15,370 / 96 / 8;
- MEMORY_ONLY: 86 / 32 / 8;
- OBJECTIVE_ONLY: 533 / 95 / 8.

### PASSIVE_TOUCH

- CONFLUENCE: 437 / 95 / 8;
- DOZ_ONLY: 146 / 70 / 8;
- FVG_ONLY: 17,718 / 96 / 8;
- MEMORY_ONLY: 80 / 25 / 8;
- OBJECTIVE_ONLY: 333 / 91 / 8.

### RECLAIM_PULLBACK

- CONFLUENCE: 343 / 94 / 8;
- DOZ_ONLY: 244 / 81 / 8;
- FVG_ONLY: 16,936 / 95 / 8;
- MEMORY_ONLY: 71 / 25 / 8;
- OBJECTIVE_ONLY: 388 / 94 / 8.

### TOUCH_NEXT_OPEN

- CONFLUENCE: 627 / 96 / 8;
- DOZ_ONLY: 422 / 90 / 8;
- FVG_ONLY: 29,714 / 96 / 8;
- MEMORY_ONLY: 125 / 38 / 8;
- OBJECTIVE_ONLY: 691 / 95 / 8.

## Exact confluence feasibility

The largest exact confluences are:

- OBJECTIVE_LIQUIDITY+FVG: 267 events / 94 sessions / 8 years;
- MEMORY+FVG: 190 / 64 / 8;
- DISPLACEMENT_ORIGIN+FVG: 131 / 66 / 8.

Other exact confluences have only 2–21 events. They remain recorded and inspectable, but are `INCONCLUSIVE` as standalone inferential cells in DEV_RANK1. They cannot be merged, dropped, or promoted after viewing COMEX outcomes merely to improve a result.

## Statistical implication

The independent unit remains the trading date/session. Event counts do not substitute for independent-session counts. DEV_RANK1 remains feature discovery only; these counts are feasibility inventory, not power claims or validation.

Canonical machine-readable source: `xau-final-results/comex_dev_rank1_gate_v1/dev_rank1_coverage_correct_daykey.json`.
