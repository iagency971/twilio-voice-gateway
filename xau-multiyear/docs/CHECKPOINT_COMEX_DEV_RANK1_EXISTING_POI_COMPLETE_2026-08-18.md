# CHECKPOINT — XAUUSD / COMEX DEV_RANK1 existing-POI research complete

Date: 2026-08-18
Branch: `agent/xau-comex-acquisition-plan`
Status: FROZEN AFTER COMPLETE DEV_RANK1 EXISTING-POI ANALYSIS

## Scope

This checkpoint closes the preregistered DEV_RANK1 question:

> Does the Phase-1 GC/COMEX information acquired for DEV_RANK1 add robust incremental predictive value to the already-defined XAUUSD reaction-zone events and frozen entry models?

It does **not** close the separate hypothesis that terminal COMEX-native levels (VWAP / POC / VAH / VAL) may define useful independent zones.

No DEV_RANK2, RETRO_CONFIRM or LOCKED_COMEX_TEST data were opened to obtain the verdict below.

## Frozen acquisition / population

- routing: `DUAL_V0_N0_CAUSAL_ACTIVE`;
- discovery period: 2011–2018;
- analytical sessions: 96;
- canonical XAU events: 31,710;
- sessions with usable primary raw GC tape: 92;
- missing/problem sessions were retained rather than replaced;
- all model evaluation is clustered by trading date and uses the frozen family/session weighting and nested leave-one-year-out procedure.

## Feature groups

- **B0**: XAU-only frozen baseline;
- **B1**: B0 + causal GC M1/context group;
- **B2**: B1 + causal GC raw-trades / auction group.

No individual COMEX feature was promoted by post-result pruning. The feature group remains the unit of inference.

## Primary target 1 — binary reaction

Population: 30,525 B2-available events / 92 sessions.

- B1 vs B0: gate FAIL.
- B2 vs B1: gate FAIL.
- B2 cluster bootstrap 95% entirely adverse.

Decision: no B1/B2 promotion.

## Primary target 2 — multiclass behavior

Target: CLEAN_REJECTION / FAILED_AUCTION / ACCEPTED_BREAK / UNRESOLVED.

- B1 vs B0: gate FAIL.
- B2 vs B1: gate FAIL.
- B2 adverse under both population and session weighting for every large family stack.

Decision: no B1/B2 promotion.

## Entry eligibility / fill

Two fill questions are statistically nontrivial at DEV_RANK1 scale:

### PASSIVE_TOUCH

- 30,525 primary comparison events / 92 sessions;
- primary fill rate ~59.10%;
- B1 vs B0: FAIL;
- B2 vs B1: FAIL;
- B2 bootstrap interval entirely adverse.

### RECLAIM_PULLBACK

- 30,127 primary comparison events / 92 sessions;
- primary fill rate ~57.81%;
- B1 vs B0: FAIL;
- B2 vs B1: FAIL;
- B2 positive years: 0/8;
- B2 bootstrap interval entirely adverse.

Other frozen entry models are either almost deterministic in fill/entry status at this population or too sparse for fill classification to become a credible alpha claim. No fill model produced a promotable COMEX feature group.

## Net-R conditional on actual entry/fill

Economic replay was rebuilt on the frozen Vantage execution overlay, not from canonical raw eligibility flags.

Frozen economic surface:

- primary costs: `S11_C6_PRIMARY` = 0.11 USD spread + 6 USD round-trip commission / 100oz lot;
- horizon: 120 minutes;
- RR: 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0;
- structural risk for PASSIVE_TOUCH / CLEAN_REJECTION / FAILED_AUCTION / ACCEPTANCE_RETEST / RECLAIM_PULLBACK;
- TOUCH_NEXT_OPEN evaluated independently under volatility floors K = 0.25 / 0.50 / 0.75 / 1.00.

The execution replay reconciles exactly to the frozen 31,710 events and 96 sessions across 2011–2018.

### Frozen plateau gate

For a B1/B2 feature group to remain eligible for DEV_RANK2 on one entry/risk rule:

1. at least 4 of 6 RR cells had to pass the already-frozen directional gate; and
2. at least one run of 3 adjacent RR values had to pass.

Each RR directional gate required simultaneously:

- family-balanced cross-fitted MSE improvement > 0;
- session-balanced cross-fitted MSE improvement > 0;
- at least 5 positive DEV years out of 8.

### Aggregate result

54 economic cells were modeled, producing 108 incremental comparisons.

There are 9 frozen entry/risk-rule combinations:

1. PASSIVE_TOUCH / STRUCTURAL;
2. CLEAN_REJECTION / STRUCTURAL;
3. FAILED_AUCTION / STRUCTURAL;
4. ACCEPTANCE_RETEST / STRUCTURAL;
5. RECLAIM_PULLBACK / STRUCTURAL;
6. TOUCH_NEXT_OPEN / K=0.25;
7. TOUCH_NEXT_OPEN / K=0.50;
8. TOUCH_NEXT_OPEN / K=0.75;
9. TOUCH_NEXT_OPEN / K=1.00.

For **every one** of these nine combinations:

- qualifying B1 RR cells = 0 / 6;
- qualifying B2 RR cells = 0 / 6;
- B1 plateau verdict = `NO_GO_DEV_RANK1`;
- B2 plateau verdict = `NO_GO_DEV_RANK1`.

Therefore the final aggregate contains 18 feature-group verdicts and all 18 are `NO_GO_DEV_RANK1`.

### Population context

Representative filled-trade populations under the primary surface include:

- PASSIVE_TOUCH: 20,890 trades / 92 sessions;
- CLEAN_REJECTION: 16,105 / 92;
- FAILED_AUCTION: 14,001 / 92;
- ACCEPTANCE_RETEST: 220 / 78;
- RECLAIM_PULLBACK: 20,074 / 92;
- TOUCH_NEXT_OPEN floors: 30,517 / 92 for each frozen K.

ACCEPTANCE_RETEST remains low-powered for excluding a small true effect, but it has no promotable B1/B2 signal and may not be opened in DEV_RANK2 as a rescue test.

## DEV_RANK1 existing-POI verdict

**NO-GO FOR DEV_RANK2 REPLICATION OF B1/B2 ON THE EXISTING XAU POI / ENTRY PATH.**

The Phase-1 COMEX groups did not merely fail to produce a robust positive plateau. Across reaction, behavior, fill and economic Net-R targets, adding B1/B2 usually worsened cross-fitted prediction relative to the simpler XAU baseline.

This is a statement about the tested incremental COMEX feature groups on the already-defined XAU POI/entry universe. It is **not** a statement that the existing price-only XAU strategies/patterns are invalid.

In particular, the historical price-only CLEAN_REJECTION findings remain separate. DEV_RANK1 says that B1/B2 COMEX does not improve their predictive economic model under the frozen protocol.

## What is forbidden after this checkpoint

Do not use DEV_RANK2 / RETRO_CONFIRM / LOCKED_COMEX_TEST to rescue the failed B1/B2 existing-POI path.

Do not:

- prune the failed B2 dictionary after seeing DEV_RANK1 and call the remainder confirmatory;
- add TBBO / MBP-1 / MBO merely because trades failed;
- pick one family, year, RR or volatility floor because it looked least bad;
- change targets, costs or gates and relabel the result as the same experiment.

Any richer order-book experiment would require a new, narrow, causally justified hypothesis with a new preregistration and independent data budget.

## Remaining independent COMEX hypothesis — native zones

The only currently preregistered COMEX path that remains scientifically independent is terminal COMEX-native source levels.

Current source registry:

- version: `COMEX_DEV_RANK1_NATIVE_SOURCE_LEVELS_V1_1`;
- usable source sessions: 92;
- source level types: VWAP / POC / VAH / VAL;
- total source levels: 368;
- exact decimal level retained;
- contact tick rounded to the valid GC 0.10 tick;
- source instrument remains the same raw contract that created the level.

Primary native retest is frozen as the first exact raw GC trade at the contact tick in the next eligible GC auction session, on the same raw source instrument.

M1 crossing is not a contact substitute.

## Next permitted work

Remain in zero-download / quote-only mode:

1. derive the next eligible raw auction session for each source session;
2. construct the raw OHLCV-1m N1 screening request manifest using the V1.1 source registry;
3. hash the manifest;
4. obtain only `metadata.get_cost()` for N1;
5. publish `download_performed=false`;
6. stop before any market-data download.

No Stage-2 native market data are authorized by this checkpoint.

## Canonical artifacts

- `CHECKPOINT_COMEX_DEV_RANK1_PRIMARY_2026-08-18.md`
- `COMEX_DEV_RANK1_ENTRY_DECISION_POPULATIONS_FREEZE_v1.md`
- `COMEX_DEV_RANK1_NET_R_SURFACE_FREEZE_v1.md`
- `COMEX_DEV_RANK1_NET_R_AGGREGATION_FREEZE_v1.md`
- `xau-final-results/comex_dev_rank1_net_r_aggregate_v1/result.json`
- `xau-final-results/comex_dev_rank1_net_r_aggregate_v1/rr_cell_summary.csv`
- `xau-final-results/comex_dev_rank1_net_r_aggregate_v1/plateau_verdicts.csv`
- `COMEX_DEV_RANK1_NATIVE_RETEST_ACQUISITION_FREEZE_v1.md`
- `xau-final-results/comex_dev_rank1_native_source_levels_v1/native_source_levels.csv`
- `xau-final-results/comex_dev_rank1_native_source_levels_v1/native_source_manifest.json`
