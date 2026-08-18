# XAUUSD Reaction Zones — COMEX DEV_RANK1 Net-R Surface Freeze v1

Date: 2026-08-18
Status: FROZEN BEFORE any COMEX-conditioned net-R regression or event-level net-R result is opened.

## Purpose

This file closes the remaining degree of freedom in the preregistered economic target: the prior research did not select one deployable target-R value. Therefore DEV_RANK1 must not choose a target R after seeing COMEX results.

Source constraints already frozen before this file:

- `COMEX_DEV_RANK1_ANALYSIS_PREREG_v1.md`: net-R is conditional on fill, modeled with ridge linear regression, with nested leave-one-year-out validation and the fixed ridge grid.
- `CHECKPOINT_PHASE_C_VANTAGE_CORRECTED_2026-08-18.md`: the robust clean-rejection result is a six-point target-R plateau and explicitly states that no single target R is selected; the plateau must be preserved through COMEX testing.

## Outcome population

For each frozen entry model, net-R is analyzed **only among filled/entered trades**.

Non-filled setups are not coded as `0 R` and are not mixed into filled-trade expectancy. Fill/retest probability remains a separate target.

The six frozen entry models remain:

- PASSIVE_TOUCH
- TOUCH_NEXT_OPEN
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTANCE_RETEST
- RECLAIM_PULLBACK

Any model/family/RR cell with inadequate fills, independent trading dates, years, or effective sample size is labeled `INCONCLUSIVE`; it is not merged opportunistically after outcomes are inspected.

## Fixed target-R surface

The economic outcome surface is frozen to the same six target-R values already present in Phase C:

`RR ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}`.

Rules:

1. All six RR outcomes are generated from the unchanged Phase-C execution engine and reported.
2. No RR is promoted merely because it is the best COMEX-conditioned historical result.
3. No single RR becomes the DEV_RANK1 primary outcome.
4. The six RRs are treated as a pre-existing robustness surface, not six opportunities to optimize an exit.
5. A COMEX economic signal cannot be promoted from an isolated RR spike.

### Supplemental anti-selection plateau guard

Because the original COMEX preregistration did not specify how to aggregate the already-frozen six-RR surface, the following additional guard is frozen now, before any COMEX net-R result is opened:

- an economic COMEX feature group may be eligible for DEV_RANK2 only if its incremental predictive direction is non-adverse on **at least 4 of the 6 fixed RR targets** under the family-balanced primary analysis;
- those non-adverse RRs must include **at least one contiguous run of 3 adjacent RR targets**;
- the preregistered temporal rule still applies: improvement cannot be driven by one year, and the corresponding primary metric must have at least 5 of 8 DEV years non-adverse unless a preregistered regime interaction applies;
- session-balanced analysis must not show a material opposite-direction result;
- an isolated RR that passes while neighboring RRs fail is audit-only and cannot promote the COMEX group.

This guard is a pre-result anti-selection rule; it is not derived from COMEX net-R outcomes.

## Execution-cost scenarios

No cost scenario is selected using COMEX results.

Frozen Phase-C/Vantage scenarios remain:

- primary: `S11_C6_PRIMARY` = 0.11 USD spread + 6 USD round-turn commission per 100 oz lot;
- sensitivity: `S10_C6` = 0.10 + 6;
- sensitivity: `S12_C6` = 0.12 + 6;
- stress: `S18_C9_STRESS` = 0.18 + 9.

Primary inference is performed on `S11_C6_PRIMARY`. Sensitivity and stress are robustness diagnostics and cannot rescue a failed primary result.

## Model and validation

For each entry model × fixed RR outcome:

- B0 = frozen XAU baseline covariates;
- B1 = B0 + frozen GC M1 context;
- B2 = B1 + frozen GC trades/auction features;
- B0/B1/B2 use exactly the same filled observations for a comparison;
- all COMEX predictors obey the model-specific causal `decision_time` cutoff and contain no post-entry information;
- ridge linear regression only;
- `C ∈ {0.01, 0.1, 1, 10, 100}`;
- outer LOYO across 2011–2018;
- C selected inside each outer fold by inner LOYO squared error;
- preprocessing fitted on training folds only.

Primary predictive comparison for the continuous net-R target is cross-fitted squared-error improvement B1 vs B0 and B2 vs B1, consistent with the preregistered ridge-selection loss. Mean net-R, PF, positive-year count, worst-year R and clustered confidence intervals remain economic diagnostics on the realized filled-trade outcomes; they do not replace the predictive gate.

No threshold on predicted expected R is selected in DEV_RANK1. If a feature group survives DEV_RANK1 and DEV_RANK2, any trade-selection threshold must be frozen later before confirm/locked testing.

## Forbidden actions

Before the six-RR COMEX net-R surface is fully reported, do not:

- choose RR 1.5, RR 2, RR 3, or any other single RR as “the” COMEX outcome;
- remove a bad RR from the surface;
- change stop, target, fill, cost, or tie-breaking rules because COMEX improves or worsens a result;
- search COMEX-dependent thresholds to maximize net-R;
- combine non-filled setups with filled-trade R;
- use RETRO_CONFIRM, DEV_RANK2, or LOCKED_COMEX_TEST to select the DEV_RANK1 economic formula.

## Interpretation

DEV_RANK1 remains feature discovery. Even a passing RR plateau is not a live strategy. It only permits a frozen COMEX feature group/formula to advance to DEV_RANK2 replication. Final strategy selection still requires broker-feed replication and genuinely prospective/virgin validation after the complete specification is frozen.
