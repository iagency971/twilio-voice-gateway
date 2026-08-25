# XAUUSD Z4 — E-BUY COVERAGE preregistration v0.3

**Frozen:** 2026-08-25 after v0.2 coverage-only failure; no reaction/trade outcome has been opened.  
**Scope:** BUY-only, outcome-blind local entry-location coverage/stability.

## Prior state

v0.2 improved the all-family architecture to 72.42% coverage inside 1.0v, 86.98% inside 1.5v and 93.09% inside 2.0v, but raw one-step persistence remained 48.72%. The gate remained FAIL. No MFE/MAE, TP/SL, reaction, future Z4 touch, future return, RR or P&L was used.

The v0.1 final coverage thresholds remain unchanged. v0.3 adds one new stateful family intended to fill the remaining local-structure gap.

## Common population

Identical to v0.1/v0.2: frozen Dukascopy BID Jan-Jul 2024, mature C5 snapshots, 08:00–17:00 New York, at least one causal Z4 strictly above current close, TR60 normalization, max local band 2.0v, max three displayed entry candidates.

## New family E — E-STRUCTURE-MEMORY (ESM)

At every mature C5 snapshot, use only data known at the snapshot.

Source: active M1.

Fixed structural windows: `{5, 10, 20, 40}` active M1 bars.

Three observation modes are tested:
1. `LOW`: minimum candle low in each window;
2. `BODYLOW`: minimum `min(open,close)` in each window;
3. `BOTH`: union of LOW and BODYLOW observations.

For each observed level:
- require `0.10v <= close - level <= 2.00v`;
- observation zone = `[level - 0.10v, level + 0.15v]` using current v;
- observations at the same snapshot are de-duplicated if intervals overlap or centers differ by <=0.15v.

### Stateful matching/lifetime

A new observation matches an existing ESM state if zones overlap or center distance <=0.20v. On match, geometry is updated to the new observation and `last_seen` is refreshed.

Grace periods tested: `{30, 60, 120}` minutes.

A state is removed at the first of:
- grace expiration since last matched observation;
- any confirmed M1 close strictly below its current frozen `zlo`.

At each C5 snapshot, active ESM states below current price and within 2.0v are ranked by nearest center and at most three are retained.

Frozen ESM grid: 3 observation modes × 3 grace periods = 9 configurations.

## Fixed prior families

No prior family is re-optimized:
- E-WICK-MEMORY fixed to v0.2 selected `EWM_G60M` with detector `EW_M1_8H_S0.25`;
- E-PIVOT-MEMORY fixed to v0.2 selected `EPM_M1_R2_A8H`;
- E-SWING fixed to v0.1 selected `ES_M1_8H_R2_T0.50`;
- Z4 below remains priority on overlap.

## ESM selection

Select the ESM configuration using outcome-blind ordering only:
1. highest 1.5v coverage;
2. highest one-step raw persistence;
3. highest 1.0v coverage;
4. lowest nearest median;
5. deterministic config ID.

## Architectures

Evaluate:
1. `Z4 + ESM` for each ESM config;
2. `Z4 + selected ESM + fixed EPM`;
3. `Z4 + selected ESM + fixed EWM`;
4. `Z4 + selected ESM + fixed EPM + fixed EWM`;
5. `Z4 + selected ESM + fixed EPM + fixed EWM + fixed E-SWING`.

De-duplication and max-three-nearest rules remain unchanged.

## Final gate — unchanged

PASS requires all:
- coverage >=80% inside 1.0v;
- coverage >=90% inside 1.5v;
- coverage >=95% inside 2.0v;
- candidate-count median 1–3;
- p90 count <=3;
- nearest-candidate p90 <=1.50v;
- raw pooled one-step 5-minute persistence >=70%.

No conditional persistence substitute is allowed in this v0.3 gate; the original stability requirement is retained.

A PASS authorizes only a separately preregistered reaction/entry-quality study.
