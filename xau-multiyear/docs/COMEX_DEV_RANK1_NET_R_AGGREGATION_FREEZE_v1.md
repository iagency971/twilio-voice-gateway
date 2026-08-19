# XAUUSD Reaction Zones — COMEX DEV_RANK1 Net-R Aggregation Freeze v1

Date: 2026-08-18
Status: FROZEN BEFORE any DEV_RANK1 COMEX-conditioned net-R result is opened.

## Purpose

This document removes the remaining orchestration ambiguity when the already-frozen six-RR economic surface is executed in parallel cells. It does not change the scientific specification in `COMEX_DEV_RANK1_NET_R_SURFACE_FREEZE_v1.md` or `COMEX_DEV_RANK1_ANALYSIS_PREREG_v1.md`.

## Cells

For each frozen entry-model / risk-rule combination, the primary cost scenario `S11_C6_PRIMARY` is evaluated at:

`RR = {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}`.

Structural models use `STRUCTURAL`. `TOUCH_NEXT_OPEN` is evaluated separately for each already-frozen volatility floor `K = {0.25, 0.50, 0.75, 1.00}`. No floor is selected from DEV_RANK1 results.

## Cell-level directional gate

For each RR and for each incremental feature-group comparison separately:

- `B1_vs_B0` = GC M1 context increment;
- `B2_vs_B1` = GC trades / auction increment.

A cell counts as a qualifying non-adverse RR only if the already-implemented `directional_gate` is true. That gate requires simultaneously:

1. family-balanced cross-fitted MSE improvement > 0;
2. session-balanced cross-fitted MSE improvement > 0;
3. at least 5 of the 8 DEV years have MSE improvement > 0.

Population-event metrics and clustered bootstrap intervals remain mandatory diagnostics but do not replace this frozen gate.

## Plateau promotion rule

A feature group is eligible to be frozen for DEV_RANK2 for one entry-model / risk-rule combination only if:

1. at least 4 of the 6 RR cells satisfy the cell-level directional gate; and
2. the qualifying RR cells contain at least one contiguous run of 3 adjacent RR values in the frozen ordered surface `[0.5, 1.0, 1.5, 2.0, 2.5, 3.0]`.

This rule is evaluated independently for `B1_vs_B0` and `B2_vs_B1`.

For `TOUCH_NEXT_OPEN`, it is evaluated independently for each frozen volatility-floor K. A passing K cannot cause another K to be removed or retroactively selected as the sole risk rule.

## Inconclusive handling

An RR cell is `INCONCLUSIVE` if the frozen model cannot be estimated because of insufficient filled events or temporal coverage.

At group level:

- `ELIGIBLE_DEV_RANK2` only if the observed modeled cells themselves satisfy the plateau rule;
- `NO_GO_DEV_RANK1` if all six RR cells are modeled and the plateau rule fails;
- `INCONCLUSIVE_DEV_RANK1` if one or more RR cells are inconclusive and the missing cells could still mathematically change the plateau verdict.

No sparse cell is merged with another family, entry model, risk rule or RR after results are seen.

## Forbidden interpretations

Do not:

- select the best single RR;
- promote an isolated positive RR;
- select one `TOUCH_NEXT_OPEN` K because it looks best;
- drop an adverse year;
- change the feature dictionary, Ridge grid, weights, clustering or cost scenario;
- use PF or in-sample mean R to override a failed predictive gate;
- open DEV_RANK2, RETRO_CONFIRM or LOCKED_COMEX_TEST to rescue a failed DEV_RANK1 group.

## Parallel execution

The six RRs may be computed as separate GitHub Actions jobs for runtime reasons. Each cell must call the same frozen functions and use the same B0/B1/B2 columns, nested leave-one-year-out procedure, `C` grid and `alpha = 1/C` mapping as `run_comex_dev_rank1_net_r_surface.py`.

Parallelization is orchestration only and must not change any observation, target, feature, weight or hyperparameter.
