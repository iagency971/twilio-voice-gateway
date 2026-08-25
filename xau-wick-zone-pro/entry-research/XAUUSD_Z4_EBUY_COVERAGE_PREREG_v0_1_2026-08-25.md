# XAUUSD Z4 — E-BUY COVERAGE preregistration v0.1

**Frozen:** 2026-08-25  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** BUY only. Outcome-blind engineering gate for entry-zone coverage.  
**Forbidden in this gate:** revisit labels, future Z4 touch, MFE/MAE, reaction/rejection, sweep/reclaim outcomes, RR, P&L, win rate, TP hit, SL hit, or any future-return selection.

## 1. Objective

Z4 is retained unchanged as the validated destination/revisit-zone engine. The present question is narrower:

> When a causal Z4 exists above current price as a potential BUY-side destination, can we display 1–3 causal zones below current price that are close enough and stable enough to be practical entry-location candidates?

This gate does **not** claim that any candidate is a profitable entry or support. It only tests whether a sufficiently dense, stable, causal entry-zone map can be constructed without degrading Z4.

## 2. Data and evaluation population

Primary source: frozen Dukascopy XAUUSD M1 BID DEV, January–July 2024, with file hashes from `results/XAUUSD_Z4_DEV_SOURCE_MANIFEST_v0_1.json`.

Z4 reference geometry:
- exact scientific grid: 0.01 USD;
- LOOKBACK = 1440 active M1;
- selected cadence = C5;
- no future-outcome function may be called;
- first 96 C5 landmarks after detector eligibility are warm-up only.

Eligible evaluation snapshots:
- confirmed C5 snapshot (`minute % 5 == 0`, UTC);
- New York session `08:00 <= local time < 17:00`;
- detector/warm-up complete;
- at least one causal Z4 strictly **above** current close at the same snapshot.

No condition is imposed on whether that upper Z4 is subsequently reached.

## 3. Normalization and local entry band

`v = median True Range over the last 60 active M1` at the snapshot.

All entry candidates must be strictly below current close. Coverage is reported at:
- 0.50 v;
- 1.00 v;
- 1.50 v;
- 2.00 v.

The candidate pool is truncated at 2.00 v below current close for this coverage gate. Z4 zones farther below remain valid Z4 objects but are not considered *local entry candidates* here.

## 4. Candidate family A — existing Z4 below

At each eligible snapshot, every existing Z4 strictly below current close is eligible. For the final local pool, retain only Z4 centers within 2.00 v below close.

Z4 is not refit, weakened, densified, or redefined.

## 5. Candidate family B — E-WICK

BUY-only local wick-density zones use **lower wicks only**. Bodies and upper wicks are excluded.

Source timeframes:
- M1;
- causal completed M5 bars aggregated from M1.

Trailing horizons:
- 4 hours: M1=240 bars, M5=48 bars;
- 8 hours: M1=480 bars, M5=96 bars.

Price grid: 0.05 USD.

For each bar, lower-wick exposure is the interval from `low` to `min(open, close)`, excluding an empty wick.

At an eligible C5 snapshot:
- form the rolling lower-wick density profile for the configuration;
- inspect only `[close - 2v, close)`;
- Gaussian smoothing sigma is either `0.25v` or `0.50v`;
- retain local peaks with positive prominence and peak density >= 2;
- zone bounds are the half-prominence width of the smoothed peak;
- require the zone to remain strictly below close;
- define `strength = prominence / sqrt(background + 1)`;
- define local rank `strength / (1 + distance_center/v)`;
- retain at most 3 E-WICK zones per configuration.

Frozen E-WICK grid: 2 TF × 2 horizons × 2 smoothing scales = 8 configurations.

## 6. Candidate family C — E-SWING

BUY-only swing zones use only **confirmed swing lows**.

Source timeframes:
- M1;
- causal completed M5 bars aggregated from M1.

Trailing horizons:
- 4 hours;
- 8 hours.

Pivot confirmation radii:
- M1: r in {2, 3};
- M5: r in {1, 2}.

A pivot low at bar `j` is causal only after the `r` bars to its right have completed. It must be strictly lower than the `r` bars on both sides.

At each snapshot:
- use only confirmed pivots inside the trailing horizon;
- retain pivot prices in `[close - 2v, close)`;
- sort prices and form contiguous clusters where adjacent pivot prices differ by at most tolerance × v;
- tolerance in {0.25v, 0.50v};
- require at least 2 pivots per cluster;
- cluster center = median pivot price;
- zone bounds = `[min(cluster)-0.10v, max(cluster)+0.10v]`;
- require center below close;
- local rank = `cluster_count / (1 + distance_center/v)`;
- retain at most 3 E-SWING zones per configuration.

Frozen E-SWING grid: 2 TF × 2 horizons × 2 pivot radii × 2 tolerances = 16 configurations.

## 7. Per-family outcome-blind configuration selection

For every E-WICK and E-SWING configuration, report:
- coverage with >=1 candidate inside 0.5v / 1.0v / 1.5v / 2.0v;
- candidate-count median and p90 inside 2.0v;
- nearest-candidate distance median / p90 in v;
- one-step 5-minute zone persistence.

Persistence is an engineering stability metric, not a price outcome. For consecutive eligible snapshots five minutes apart, a zone at t persists if at least one zone of the same configuration at t+5 overlaps it or has center distance <= `0.25 * max(v_t, v_t+5)`.

Frozen family selection order:
1. highest coverage inside 1.5v;
2. highest one-step persistence;
3. highest coverage inside 1.0v;
4. lowest nearest-distance median;
5. lowest configuration ID as deterministic tie-break.

No reaction or future-price outcome may enter selection.

## 8. Final pool construction

Evaluate these architectures:
1. `Z4_BELOW_ONLY`;
2. `Z4_BELOW + selected E-WICK`;
3. `Z4_BELOW + selected E-SWING`;
4. `Z4_BELOW + selected E-WICK + selected E-SWING`.

For a combined pool at a snapshot:
- include only candidate centers within 2.0v below close;
- Z4 below has representation priority when a supplementary zone overlaps it;
- otherwise de-duplicate zones if they overlap or their centers differ by <=0.20v;
- after de-duplication retain the **3 nearest** zones below price.

This maximum of three is frozen before reaction testing.

## 9. Final E-BUY COVERAGE gate

A final architecture passes only if all are true:
- coverage >= **80%** with >=1 candidate inside 1.0v;
- coverage >= **90%** with >=1 candidate inside 1.5v;
- coverage >= **95%** with >=1 candidate inside 2.0v;
- candidate-count median inside 2.0v is between **1 and 3**;
- candidate-count p90 inside 2.0v <= **3**;
- nearest-candidate p90 <= **1.50v**;
- one-step 5-minute pooled zone persistence >= **70%**.

Selection among passing architectures:
1. fewest supplementary families;
2. highest persistence;
3. highest 1.0v coverage;
4. highest 1.5v coverage;
5. lowest nearest-distance median;
6. deterministic architecture name.

If none passes: `EBUY_COVERAGE_FAIL` and no reaction study is authorized without a new preregistration.

If one passes: `EBUY_COVERAGE_PASS`. This only authorizes a **separate preregistered reaction/entry study**. It does not authorize live entry signals.

## 10. BUY-only relationship to later route/TP research

The presence of an upper Z4 is used here only to define the relevant BUY-side context. This v0.1 gate does not yet estimate `R_US`, `UP_FIRST`, `DOWN_FIRST`, or end-of-session TP success. Those are separate future-outcome questions and must remain separate from this coverage selection.
