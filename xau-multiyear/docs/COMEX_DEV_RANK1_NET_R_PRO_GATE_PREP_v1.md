# COMEX DEV_RANK1 — net-R Pro gate preparation v1

Date: 2026-08-18 America/Guadeloupe
Status: PRE-OUTCOME METHODOLOGY ONLY

No COMEX-conditioned P&L/net-R result has been computed or inspected under this gate preparation.
No Databento call or purchase is authorized by this document.

## Purpose

Before testing whether COMEX features improve realized trading expectancy conditional on entry/fill, freeze an outcome definition that cannot be chosen after observing COMEX-conditioned P&L.

## Already frozen upstream

- Entry models: PASSIVE_TOUCH, TOUCH_NEXT_OPEN, CLEAN_REJECTION, FAILED_AUCTION, ACCEPTANCE_RETEST, RECLAIM_PULLBACK.
- Model-specific causal decision times are fixed.
- COMEX feature groups are fixed as B0 (XAU baseline), B1 (GC continuous M1 context), B2 (B1 + active raw DUAL tape/profile).
- Existing reaction and multiclass behavior targets are NO-GO and may not be retuned.
- Fill target uses nested LOYO and same-sample B0/B1/B2 comparisons.
- Broker primary cost scenario from prior Phase C research is S11_C6_PRIMARY (XAU spread $0.11 + $6 round-trip commission); stress scenario S18_C9 is retained as stress only.
- Prior Phase C explored RR values 0.5, 1.0, 1.5, 2.0, 2.5, 3.0. Those price-only results have already been seen historically and therefore cannot be used now to choose whichever RR is most favorable to COMEX.

## Methodological problem requiring Pro decision

A single post-hoc RR would create outcome-selection bias. Conversely, treating six RRs as six independent chances to pass would create multiplicity and winner-selection bias.

The Pro audit must select one prespecified approach before any COMEX-conditioned net-R results are calculated:

### Candidate A — Fixed reference RR independent of COMEX
Select one RR by an exogenous/preregistered scientific rule, not by historical COMEX or price-only winner status, then evaluate incremental B1 vs B0 and B2 vs B1 on net-R conditional on fill.

### Candidate B — Full frozen RR vector, no winner selection
Evaluate all six previously frozen RR outcomes as a multivariate robustness surface. No RR can be promoted alone. Promotion requires a preregistered joint criterion/multiplicity rule and economic consistency across a specified subset or the whole vector.

### Candidate C — RR-free economic target first
Use an outcome such as signed MFE/MAE, terminal R at a fixed horizon, or another fixed path-functional defined before COMEX results, then use the old RR grid only as secondary sensitivity. This would require a precise causal/execution definition and must not be invented after looking at P&L.

## Questions for Pro

1. Which candidate best measures incremental COMEX economic value without outcome-selection bias?
2. Should S11_C6_PRIMARY remain the sole primary cost scenario and S18_C9 a mandatory stress sensitivity?
3. What is the primary estimand: mean net-R per filled trade, session-balanced net-R, family-balanced net-R, or a hierarchy of these?
4. How should clustering by trading date be incorporated for continuous net-R outcomes?
5. Should the economic model predict realized net-R directly, classify positive net-R, rank trades, or estimate heterogeneous treatment/value? Only one primary formulation should be chosen.
6. How are fills handled: analysis strictly conditional on fill, with fill model reported separately, versus an unconditional decision-value target assigning zero to no-fill? These answer different questions and should not be conflated.
7. How should the six entry models be handled for multiplicity? No model may be selected because it historically performed best in price-only research.
8. What minimum sample size / independent-session count is required for an economic conclusion by model/family?
9. What is the exact promotion gate to DEV_RANK2? It must be strong enough that a single noisy positive cell cannot justify more data spend.
10. Should the three quasi-deterministic fill models (TOUCH_NEXT_OPEN, CLEAN_REJECTION, FAILED_AUCTION) proceed directly to conditional net-R while PASSIVE_TOUCH/RECLAIM_PULLBACK/ACCEPTANCE_RETEST retain separate fill conclusions?

## Guardrails

- No RR chosen because DOZ_OBJECTIVE/CLEAN_REJECTION or any old price-only setup looked profitable.
- No COMEX feature threshold/quantile is chosen from realized P&L before the model-selection procedure is frozen.
- No family is removed because price-only or COMEX reaction results were poor.
- Sparse cells are labeled underpowered/inconclusive.
- DEV_RANK2 remains unopened and is a replication block, not a tuning block.
- RETRO_CONFIRM and LOCKED_TEST remain unopened.
- Native COMEX zones remain a separate scientific axis; failure on existing XAU POIs does not invalidate native-zone research.
