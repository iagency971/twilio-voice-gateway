# V14 — Six-model US100 segmentation diagnostic

## Purpose
Diagnostic decomposition of the already-selected V12/V13 six-model FTMO candidate. This is NOT a new optimization or validation gate and MUST NOT be used to claim a newly filtered strategy is validated retrospectively.

## Frozen candidate
Models:
- ema_rev
- kalman_mom
- open_drive
- ou_rev
- pd_rev
- pm_mom

Risk reference: 0.80% per trade on a 10k FTMO-style account.
Source ledger: `us100-zero-data/results/native_12model_port_v5/TRADES_RESCORED.csv`.
The candidate was selected before this diagnostic. No signal parameters are changed.

## Partitions
All available candidate trades are analyzed descriptively, with stability broken out by:
- DEV: 2021–2023
- VAL2024: 2024
- VAL2025: available Jan–Apr 2025

Because aggregate 2024/2025 outcomes have already been observed, this analysis is diagnostic rather than fresh OOS evidence.

## Required segmentations
1. Direction: LONG vs SHORT.
2. Model.
3. Model × direction.
4. New York entry-time buckets:
   - OPEN_0930_1030
   - MORNING_1030_1200
   - LUNCH_1200_1330
   - PM_1330_1500
   - POWER_1500_1600
   - OTHER
5. Entry hour (NY wall clock).
6. Weekday.
7. Exit reason.
8. Risk-width quartile using `risk_ticks` within the six-model candidate.
9. Period stability (DEV / 2024 / 2025) for direction, session, and model × direction.

## Metrics
For every sufficiently populated segment:
- N
- PRIMARY and STRESS mean R, total R, PF, win rate, max closed-trade DD, losing streak
- share of trades and share of STRESS total R
- scaled DD at 0.80% risk
- STRESS R per complete session where meaningful

## Marginal contribution analysis
For each direction, session bucket, and model:
- recompute the whole six-model portfolio after removing that segment
- report remaining N, STRESS mean R, PF, max DD, total R
- report change in total R, PF, DD, and implied Step-1 pace at fixed 0.80% risk

This is descriptive only. A segment that looks removable after seeing these outcomes must be treated as a new hypothesis and validated prospectively (FTMO Free Trial / forward), not retroactively promoted as validated.

## Interpretation priorities
1. Does one direction materially dominate and remain positive in DEV, 2024, and 2025?
2. Are there time buckets that are persistently weak or loss-making?
3. Which models/directions contribute disproportionately to DD relative to R?
4. Does removing a segment improve expected FTMO pace, rather than merely improve PF?
5. Avoid conclusions from tiny-N cells; flag N<30 as low-confidence and N<15 as very-low-confidence.
