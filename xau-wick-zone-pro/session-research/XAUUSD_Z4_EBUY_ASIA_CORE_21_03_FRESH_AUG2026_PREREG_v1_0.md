# XAUUSD Z4 / E-BUY — Asia Core 21:00–03:00 NY fresh Aug-2026 holdout prereg v1.0

**Frozen:** 2026-08-26, after the Asia v2 45-candidate architecture grid returned zero H1+H2 passers and after the outcome-blind fixed-subperiod diagnostic, but before any Asia-Core August-2026 zone metric or reaction outcome is generated or inspected.

## 1. Status of the hypothesis

The candidate window `21:00–03:00 America/New_York` is **data-derived** from the already-exposed H1/H2 outcome-blind diagnostic: the `18:00–21:00` slice was the clear localization weakness, whereas `21:00–00:00` passed the three coverage bands in H1/H2 and `00:00–03:00` was near-pass/pass.

Therefore H1/H2 cannot validate this new window. The new test uses August 2026 data that was not part of Asia v1/v2 (which ended 2026-07-31 UTC).

## 2. Frozen window and architecture

- Session candidate: **ASIA CORE = 21:00 <= NY time < 24:00 OR 00:00 <= NY time < 03:00**.
- Session identity = New York calendar date on which the 21:00 segment begins.
- Cadence = C5.
- Architecture = current/best Asia v1 architecture, unchanged: `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`.
- Top-3 display, `0 < distance <= 2.0v`, v0.4 sticky carry, 0.20v de-duplication, Z4 priority, 96-C5 warm-up, all unchanged.
- No E score.
- No architecture re-search on the holdout.

The Asia v2 45-candidate grid found no robust H1+H2 alternative; the current full `BOTH_G120M` architecture remained the best worst-window 1v coverage candidate. This holdout tests the **time-window hypothesis only**.

## 3. Frozen data source

Warm-up source:
- `xauusd_bid_m1_2026_07.csv`, exact SHA-256 already frozen in the historical source manifest: `1861d23f4edbaa9cc5c5ca2bd419c9a7d54ef60299a75c5d4e8e8681bd308286`.

Holdout source:
- `https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd/bid/m1/xauusd_bid_m1_2026_08.csv`.

The workflow must download the August file and compute/write its raw SHA-256 **before any zone metric is calculated**. All data present in that exact downloaded byte stream are frozen for this run; no date truncation may be chosen after metrics are seen.

Only **complete 21:00–03:00 NY sessions fully contained in the August byte stream** are eligible. Partial first/last sessions are excluded mechanically before metrics. July is warm-up only and is excluded from holdout metrics.

## 4. Z4 provenance

Generate C5 Z4 geometry from the frozen canonical detector using the same source-faithful geometry-only transformations used by current E-BUY OOS evidence:
- cadence literal to C5;
- no future-reaction guard for geometry-only state;
- no reaction/outcome computation;
- detector density/smoothing/peak/boundary/side rules unchanged.

July+August are processed continuously; only August complete-session snapshots enter the holdout metrics.

## 5. Frozen location/stability gate

Use the same eight pre-existing E-BUY operational thresholds:
1. coverage <=1.0v >=0.80;
2. coverage <=1.5v >=0.90;
3. coverage <=2.0v >=0.95;
4. displayed-zone count median between 1 and 3;
5. displayed-zone count p90 <=3;
6. nearest-zone distance p90 <=1.5v;
7. survival-aware display persistence >=0.70;
8. unexplained disappearance share of survival-eligible transitions <=0.05.

Report also complete session count, eligible snapshot count, zero-display share, mean zone count, family mix, raw persistence and runtime.

No threshold may be changed because the holdout is small or because a result is close.

## 6. Interpretation

- PASS = `ASIA_CORE_FRESH_AUG2026_LOCATION_PASS` only if all eight checks pass.
- FAIL = `ASIA_CORE_FRESH_AUG2026_LOCATION_FAIL` otherwise.

Because August 2026 is a partial-month holdout, even a PASS is supporting fresh evidence, not automatic production authorization.

A BULL_REJECTION reaction study may be opened only after a location PASS and must use the final repaired pre-outcome reaction semantics (`xau_ebuy_reaction_dev_v1_0_3_final_preoutcome`) adapted only to the fixed 21:00–03:00 boundary. No reaction outcome is opened in the location gate itself.