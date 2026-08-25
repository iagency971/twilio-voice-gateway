# XAUUSD Z4 — E-BUY COVERAGE preregistration v0.2

**Frozen:** 2026-08-25, after v0.1 coverage-only result and before any reaction/price-outcome study.  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** BUY only; outcome-blind coverage/stability repair.

## Why v0.2 exists

v0.1 used no future price outcomes and returned `EBUY_COVERAGE_FAIL`. The combined Z4 + selected E-WICK + selected E-SWING architecture reached only 65.40% coverage inside 1.0v, 82.17% inside 1.5v, 88.70% inside 2.0v and 47.40% one-step persistence. Existing Z4 below alone reached only 15.42% inside 2.0v.

The repair hypothesis is therefore **state persistence**, not reaction quality: recomputed local-density/cluster zones are too sparse and transient for an entry-location map. No MFE/MAE, reaction, future TP/SL, revisit, P&L or future return has been consulted.

The final gate thresholds from v0.1 are **unchanged**.

## Frozen common population

Exactly the same population as v0.1:
- Dukascopy XAUUSD BID Jan-Jul 2024 frozen DEV;
- C5 snapshots;
- 08:00 <= America/New_York < 17:00;
- Z4 LOOKBACK 1440 active M1;
- first 96 C5 landmarks warm-up;
- at least one causal Z4 strictly above current close;
- `v = median TR60 active M1`;
- local entry band <=2.0v below close.

Z4 below remains candidate family A and retains representation priority on overlap.

## Family D — E-PIVOT-MEMORY

A stateful BUY-only support-location family is added. It uses only confirmed historical swing lows and current/past closes.

Source timeframes:
- M1;
- causal completed M5 bars aggregated from M1.

Pivot confirmation radii:
- M1 r in {2,3};
- M5 r in {1,2}.

A pivot at source bar j is created only after r bars to its right have completed and its low is strictly lower than the r lows on both sides.

### Zone creation

At pivot confirmation time:
- center = pivot low;
- `v_create` = current causal M1 TR60 normalizer;
- zone = `[center - 0.10*v_create, center + 0.20*v_create]`;
- creation uses no future information beyond the bars required for pivot confirmation.

### Stateful lifetime

Age caps tested outcome-blind:
- 2 hours;
- 4 hours;
- 8 hours.

A created zone remains active until the first of:
1. age cap expires; or
2. a confirmed M1 close is strictly below its frozen `zlo`.

No reaction, bounce or subsequent favorable movement is required to keep or remove a zone.

At an evaluation snapshot, retain active zones whose centers are strictly below current close and within 2.0v. Rank by:

`rank = 1 / ((1 + distance_center/v) * (1 + age_hours/age_cap_hours))`

Retain at most three before cross-family de-duplication.

Frozen grid: 2 source TF × 2 pivot radii × 3 age caps = 12 E-PIVOT-MEMORY configurations.

## Family B2 — E-WICK-MEMORY

Use the v0.1 outcome-blind selected E-WICK detector configuration **without re-selection**:

`EW_M1_8H_S0.25`.

When this detector emits a zone at a C5 snapshot, create/update a state object by overlap or center distance <=0.25v. A state is retained through temporary detector disappearance for a grace period in:
- 15 min;
- 30 min;
- 60 min.

The state is removed earlier if a confirmed M1 close is strictly below its frozen/current `zlo`.

State geometry is updated only when the detector re-matches it; otherwise it is carried unchanged. At most three active E-WICK-MEMORY zones inside 2.0v are retained by nearest distance.

Frozen grid: 3 grace periods.

## Fixed v0.1 support family

The v0.1 selected E-SWING configuration `ES_M1_8H_R2_T0.50` is retained as a fixed comparison only. It is not re-optimized in v0.2.

## Architectures evaluated

1. `Z4_ONLY`;
2. `Z4 + E-PIVOT-MEMORY` for each of 12 configs;
3. `Z4 + E-WICK-MEMORY` for each of 3 grace configs;
4. `Z4 + E-PIVOT-MEMORY + E-WICK-MEMORY` using the individually selected stateful configs;
5. `Z4 + E-PIVOT-MEMORY + fixed E-SWING`;
6. `Z4 + E-PIVOT-MEMORY + E-WICK-MEMORY + fixed E-SWING`.

Cross-family de-duplication and max-three-nearest display rule remain exactly as v0.1.

## Outcome-blind configuration selection

For E-PIVOT-MEMORY and E-WICK-MEMORY individually, use the same family ordering as v0.1:
1. highest coverage inside 1.5v;
2. highest one-step persistence;
3. highest coverage inside 1.0v;
4. lowest nearest-distance median;
5. deterministic config ID.

## Final gate — unchanged from v0.1

PASS requires all:
- coverage >=80% inside 1.0v;
- coverage >=90% inside 1.5v;
- coverage >=95% inside 2.0v;
- candidate-count median in [1,3];
- p90 count <=3;
- nearest-candidate p90 <=1.50v;
- pooled one-step 5-minute persistence >=70%.

Among passers choose fewest supplementary families first, then highest persistence, highest 1.0v coverage, highest 1.5v coverage, lowest nearest median, deterministic name.

`EBUY_COVERAGE_PASS` authorizes only a separately preregistered reaction/entry study. It is not an entry signal.
