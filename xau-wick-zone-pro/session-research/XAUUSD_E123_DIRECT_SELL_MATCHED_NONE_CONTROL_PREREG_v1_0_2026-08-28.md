# XAUUSD direct E1/E2/E3 SELL — matched non-E bearish-rejection control preregistration v1.0

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`
Status: **FROZEN BEFORE CONTROL OUTCOMES**

## Purpose

The prior retrospective direct-SELL study found positive structural expectancy for bearish-rejection SELLs on causal sticky E1/E2/E3 resistance zones located strictly between two Z4 intervals or above the highest Z4. This control asks the missing incremental-information question:

> Does contact with a causal E zone add information beyond an otherwise comparable bearish BR70 rejection occurring in the same Z4 geometry?

This study does **not** alter, optimize, rescore or refit E1/E2/E3.

## Frozen treated cohort

Source is the immutable direct-E SELL evidence from workflow run `33193034282`, generated under:

- prereg: `XAUUSD_E123_DIRECT_SELL_BETWEEN_ABOVE_Z4_PREREG_v1_0_2026-08-28.md`, blob `3c39c1162c6b5f84c76d8253dc39ca9c718f1347`;
- frozen engine: `xau_e123_direct_sell_between_above_z4_v1_0.py`, blob `60e6783f8c4e530ae403fa298b8abf3959e08518`;
- causal sticky E architecture blobs `ef45037d2a99a705ddf9bfbc3ebc666f88119a80` and `bfb0d65efce0f5773b2045eaf4c31ed6bc07740f`.

Treated observations are executed direct-E SELL trades exactly as recorded. No treated trade may be added, removed or reclassified except for prespecified H1/H2/geometry slicing.

Primary treated geometry: `BETWEEN_Z4_STRICT`, all E1/E2/E3 ranks pooled.

Secondary treated geometry: `ABOVE_HIGHEST_Z4_STRICT`.

Historical windows remain:
- H1: 2024-08-01 to 2025-08-01 UTC;
- H2: 2025-08-01 to 2026-08-01 UTC.

Sessions remain US 08-17 NY, Asia broad 18-03 NY, Asia Core standalone 21-03 NY, Europe 03-08 NY.

## Frozen control-event definition

For every M1 in the same causal state reconstruction:

1. bar is inside the selected session;
2. bearish BR70 is true: `close < open` and `(high-close)/(high-low) >= 0.70`;
3. the bar range **does not intersect any currently displayed causal SELL E1/E2/E3 zone**. This is the non-E condition; touching an E of any rank excludes the bar from the control pool;
4. define control anchor = trigger-bar `high`;
5. using only causal Z4 known at that bar:
   - `BETWEEN_Z4_STRICT`: anchor lies strictly in the open gap between two adjacent Z4 intervals; target is the adjacent lower Z4 upper boundary;
   - `ABOVE_HIGHEST_Z4_STRICT`: anchor lies strictly above the highest Z4 upper boundary; target is that highest Z4 upper boundary;
6. target must not already have been touched on the trigger bar;
7. entry = next M1 open inside the same session and must remain above target.

No control signal uses future data for eligibility, target or matching covariates.

## Structural target identity

A treated and control event are considered to reference the same target Z4 when their frozen target intervals overlap OR their target centers differ by at most `0.25 * max(v_treated, v_control)`.

This target-identity rule is frozen before control outcomes and mirrors the structural identity tolerance already used elsewhere in the E/Z4 research.

## Primary matching

Matching is performed separately within each H1/H2 window, session definition and session-id/day.

A treated E trade can match a control only if:

- same geometry class;
- same structural target Z4 identity;
- absolute trigger-time difference <= 180 minutes.

Controls are used at most once.

Within each session-id, use deterministic global minimum-cost bipartite assignment (`scipy.optimize.linear_sum_assignment`) over admissible edges. Edge cost is:

`0.50 * abs(target_distance_v_E - target_distance_v_C)`
`+ 0.30 * abs(down_close_position_E - down_close_position_C)`
`+ 0.20 * abs(minutes_time_difference) / 180`.

Impossible edges receive infinite cost and are not matched. Ties are broken deterministically by treated trigger time then control trigger time.

No outcome variable enters matching.

## Risk matching / control stop

A non-E rejection has no E boundary, so using candle high or an arbitrary fixed stop would confound signal quality with stop design.

For each matched pair, the control receives the **same normalized risk budget** as its treated E trade:

`control_stop_distance = treated_stop_distance_v * control_v`.

Thus:

`control_stop = control_entry + control_stop_distance`.

The control target remains its own frozen adjacent lower Z4 target. Control nominal RR is therefore `control_target_distance / control_stop_distance`.

This isolates the incremental value of E contact while matching stop budget in local-volatility units. No control outcome is consulted when assigning the stop.

## Outcome scan

From next-open entry to same-session end:

- TP = first low touching frozen target upper boundary;
- invalidation = first confirmed M1 close strictly above the matched frozen stop; wicks above stop are allowed for exact structural comparability;
- same M1 TP + close invalidation = `AMBIGUOUS`;
- if neither occurs before session end = `NEITHER`.

Treated outcomes remain exactly those already recorded by the prior frozen engine.

## Prespecified metrics

### Primary estimand

`BETWEEN_Z4_STRICT`, all four sessions pooled, reported separately H1 and H2 and pooled only as support.

For each non-ambiguous matched pair define conservative session R:
- TP_FIRST: `+nominal_rr`;
- INVALIDATION_FIRST: `-1`;
- NEITHER: `0`.

Primary effect = mean paired difference `R_E - R_control`.

Also report:
- matched treated count and matching coverage;
- TP-first probability treating NEITHER as non-TP;
- paired TP probability difference;
- terminal-only TP rate and terminal-only expectancy as compatibility diagnostics with the prior study;
- PF_R for each arm;
- distributions of target_distance_v, stop_distance_v, down_close_position and time difference after matching.

### Secondary analyses

- same matched analysis for `ABOVE_HIGHEST_Z4_STRICT`;
- session-specific results for both geometries;
- E1/E2/E3 treated rank only as descriptive stratification, never as a new optimized filter.

## Uncertainty

Use 2,000 deterministic-seed (`20260828`) cluster bootstraps by session-id/day on matched pairs. Report 95% percentile interval for mean paired R difference and TP-probability difference.

## Frozen interpretation gate

This historical control can support an **incremental E-contact claim**, but can never authorize production by itself because the control question was formulated after observing the earlier direct-E outcomes.

Primary BETWEEN-Z4 historical incremental support requires all of:

1. matching coverage >= 50% in H1 and H2;
2. mean paired R difference > 0 in H1 and H2;
3. pooled mean paired R difference > 0 with cluster-bootstrap 95% lower bound > 0;
4. paired TP-probability difference is not directionally negative in either H1 or H2.

If these fail, the direct-E edge must be treated as explainable by general Z4-gap bearish-rejection geometry until further evidence.

Even if they pass, status is only `HISTORICAL_INCREMENTAL_E_CONTACT_SUPPORTED_PENDING_FUTURE_CONFIRMATION`.

Production authorization: **NONE_CONTROL_STUDY_ONLY**.
