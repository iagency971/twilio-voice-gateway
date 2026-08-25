# XAUUSD Z4 — E-BUY COVERAGE OOS replication preregistration v1.0

**Frozen:** 2026-08-25 after DEV v0.4 coverage PASS; before any E-BUY reaction/TP/trade outcome is opened.  
**Scope:** BUY-only coverage/stability replication, no parameter selection.

## Frozen architecture

No architecture or parameter may change from DEV v0.4:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

Display rule: frozen v0.4 sticky top-3.

Z4: exact scientific 0.01 USD geometry, LOOKBACK 1440 active M1, C5 cadence, 96 C5 landmark warm-up, no future-outcome function.

Local E-BUY band: strictly below close and within 2.0 TR60 units (`v`). Maximum displayed candidates = 3.

## Data

Primary source: exact frozen Dukascopy XAUUSD BID files from `cadence-sensitivity/c5-replication-v0-2/XAUUSD_Z4_C5_HISTORICAL_SOURCE_MANIFEST_v0_2.json`.

Use continuous BID data from 2024-08 through 2026-07 inclusive. Every downloaded monthly file must match its frozen SHA-256 in the manifest before any calculation.

No ASK or FOREXCOM data enters this primary replication.

## Evaluation windows fixed before results

The engine runs continuously across the full 24 months. Evaluation is then split without resetting generators at the boundary:

- `OOS_H1`: 2024-08-01 00:00 UTC <= t < 2025-08-01 00:00 UTC.
- `OOS_H2`: 2025-08-01 00:00 UTC <= t < 2026-08-01 00:00 UTC.
- `OOS_ALL`: union of H1 and H2, reported as support only.

Eligible snapshots inside each window remain identical to DEV:
- mature confirmed C5 snapshot;
- New York 08:00 <= local time <17:00;
- at least one causal Z4 strictly above current close.

## Frozen replication metrics and thresholds

For each of H1 and H2 separately, require all DEV v0.4 gates:

- coverage >=80% inside 1.0v;
- coverage >=90% inside 1.5v;
- coverage >=95% inside 2.0v;
- candidate-count median between 1 and 3;
- candidate-count p90 <=3;
- nearest-candidate p90 <=1.50v;
- survival-aware display persistence >=70%;
- unexplained disappearance share of survival-eligible transitions <=5%.

Raw display persistence remains diagnostic only.

## Verdict

`EBUY_COVERAGE_OOS_REPLICATION_PASS` only if **both OOS_H1 and OOS_H2 pass every gate**.

A PASS freezes E-BUY v0.4 as the location engine for the subsequent reaction study. H1 may then be used as reaction-development data and H2 must remain untouched as reaction holdout until a reaction model/trigger is preregistered and frozen.

A FAIL prohibits opening reaction outcomes until the coverage failure is diagnosed outcome-blind. No post-hoc family/parameter rescue is allowed within this replication.

## Forbidden information

During this replication, do not compute or inspect E-zone reaction/rejection, future upper-Z4 hit, first-route outcome, MFE/MAE, favorable/adverse excursion, TP/SL, RR, P&L, win rate, or future return.