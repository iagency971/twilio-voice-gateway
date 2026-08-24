# XAUUSD Z4 validated Revisit Score → Pine port spec v0.1

**Date:** 2026-08-23  
**Status:** IMPLEMENTATION SPEC FROZEN BEFORE PINE QA  
**Scientific scope:** M1 `P_REVISIT_240` only.

## 1. User-visible modes

### M1 validated-score mode

On a 1-minute XAUUSD chart the indicator may display Z4 zones and `R xx`, where `R` is the frozen DEV-percentile **Revisit Score H240**.

`R` never carries a `%` sign and is never called reaction strength.

### Higher-timeframe descriptive mode

M5/M15/H1+ may continue to show descriptive native wick-density zones if desired, but **must not display R** until separately validated. The UI must visibly state that higher-TF zones are descriptive/unvalidated.

## 2. Frozen M1 construction

- 1,440 active M1 observations (`high > low`).
- v60 = median TR of latest 60 active M1, minimum 20.
- vseg = median TR of latest 1,440 active M1, minimum 240.
- 15-minute UTC landmark cadence (`minute % 15 == 0`).
- absolute price-grid alignment at multiples of the selected outcome-blind grid step.
- smoothing = already parity-approved 3-box Gaussian proxy.
- family/medium-peak/fine-confirmation/prominence/P50 logic must follow frozen Z4 semantics.
- no Top N.

The grid step is not hand-tuned in Pine. It is the deterministic result of `XAUUSD_Z4_PINE_GRID_STEP_PREREG_v0_1.md`; if no coarser candidate passes, 0.01 remains mandatory.

## 3. Lineage state

- one-to-one matching only against the immediately preceding eligible 15-minute snapshot;
- match valid if center distance ≤ max(vseg_prev,vseg_cur) OR intervals overlap;
- cost = distance/vseg + 0.5*(1-IoU) + 0.1*abs(log(width_cur/width_prev));
- deterministic minimum-cost one-to-one assignment;
- a missing eligible snapshot terminates all prior lineages;
- warm-up state cap = **96 eligible landmarks**, selected by a preregistered outcome-blind gate with effectively exact frozen-score parity.

The Pine implementation may use a deterministic greedy equivalent only if a separate outcome-blind assignment-parity gate demonstrates equivalence to Hungarian Z4. Otherwise exact one-to-one minimum-cost assignment must be implemented.

## 4. Frozen score

Use the frozen BID M0GL scaler, coefficients and intercept from:

`results/XAUUSD_Z4_FROZEN_MODEL_PARAMS_v0_1.json`

No coefficient may be edited in Pine for visual preference.

Map the raw logistic output through the frozen equal-landmark-weighted DEV percentile thresholds from:

`results/XAUUSD_Z4_REVISIT_SCORE_MAP_v0_1.json`

to obtain `R 0–100`.

## 5. Score update semantics

- Recompute validated R only on an eligible 15-minute landmark.
- Between landmarks hold the last scored Z4 snapshot visually; do not pretend it was freshly re-estimated each minute.
- A zone that disappears at the next frozen snapshot disappears/terminates according to Z4; no visual hysteresis may modify the scientific state.
- Optional descriptive every-M1 overlays must be visually distinguishable from frozen R-scored zones.

## 6. QA / fail-closed behavior

The indicator must not silently change scientific parameters to fit Pine limits.

If any condition prevents faithful calculation (insufficient active history, price grid exceeding implementation capacity, lineage warm-up incomplete, unsupported timeframe), the validated R score is shown as **unavailable**, not approximated with a different lookback/step.

Debug mode must expose at least:
- active bars available;
- v60;
- vseg;
- grid step and grid levels;
- snapshot timestamp;
- current zone count;
- lineage warm-up landmarks completed;
- score-status (`VALIDATED_PROXY`, `WARMUP`, `GRID_LIMIT`, `NON_M1`).

## 7. Feed limitation

Scientific validation used Dukascopy XAUUSD BID as primary and Dukascopy ASK as secondary robustness. A TradingView broker feed is not automatically equivalent. Until cross-feed parity is measured, the Pine UI/documentation must state that model validity is established on Dukascopy M1 and that use on another chart feed is a transfer assumption, not a newly validated result.

## 8. Final implementation gate

Before calling the Pine score implementation validated, compare Pine-emulated/Pine-produced zones and R scores against the frozen Python proxy at preregistered timestamps without using future outcomes. Required checks will include geometry, lineage IDs/state, raw M0GL score and R score. Failure means the Pine port remains QA-only.
