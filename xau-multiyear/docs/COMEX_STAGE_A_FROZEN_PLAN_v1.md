# COMEX Stage A frozen acquisition plan v1

Date: 2026-08-18
Status: preregistered acquisition/analysis staging only. No Databento market-data download authorized or performed.

## Purpose

Avoid spending the full historical-tick budget before establishing whether centralized GC information has useful incremental signal, without allowing post-COMEX adaptive sample selection.

## Stage A — frozen base panel

Acquire only after explicit user authorization:

1. `GC.v.0` `ohlcv-1m`, 2010-06-06 through 2026-08-17 — exact metadata quote: USD 20.342466905713.
2. `GC.v.0` `bbo-1m`, same period — exact metadata quote: USD 7.630651295185.
3. `GC.v.0` `trades` on the frozen session-panel Tier 2 — 357 complete wide session envelopes — exact metadata quote: USD 39.918261766426.

Exact quoted Stage A total: **USD 67.891379967324**.

The wide session envelope is 17:00 New York on the previous calendar day through 18:00 New York on the research trading date. This is deliberately conservative for historical session-hour differences; no attempt is made to infer unavailable trades in maintenance gaps.

## Stage B — frozen supplement before Stage A outcomes

The deterministic V2 supplement pool is already frozen with seed `COMEX_SUPPLEMENT_V2_SEED_971`, using no COMEX market-data outcomes. It includes:

- screening targets for pure DOZ, OBJECTIVE and MEMORY signatures;
- screening targets for abundant FVG confluences;
- all rare confluence signatures outside the base session panel;
- explicit ACCEPTANCE_RETEST supplements where the base panel is deficient;
- no generic FVG-only local expansion because Tier 2 complete sessions already provide a very large FVG-only tick sample.

Stage B local scientific windows remain `contact -30m / +16m`, snapped outward to 10-minute request boundaries. Tier 2 / merge-gap 30m is the current exact-cost candidate.

**Stage B selection must not be changed after Stage A COMEX outcomes are inspected.** Acquisition of all or a preregistered subset may be conditioned only on the rules below.

## Stage A analysis rules

Analyze price-only baseline versus incremental COMEX feature groups without changing the event sample:

- M1 context: GC price/range/volume, relative volume, BBO M1, GC-XAU basis;
- local time-and-sales available inside complete sessions: volume, trade count, aggressor delta subject to side QA, local CVD, trade-size distribution, local volume-at-price and local profile measures;
- complete-session profile: exact session VWAP, POC/VAH/VAL/HVN/LVN, session CVD and value migration.

Use the frozen temporal split labels. The 2023-2025 `COMEX_FEATURE_HOLDOUT` is a holdout for COMEX feature development only; it is not a virgin strategy holdout because XAU outcomes have already been inspected historically.

## Stage B trigger rule

Stage B is justified if at least one of the following is true after Stage A:

1. a predeclared COMEX feature group shows temporally coherent incremental value and additional sample is needed for estimation/validation;
2. a family/model cell is explicitly underpowered in Stage A and remains scientifically material to the all-family/all-entry objective;
3. the COMEX-native-zone panel identifies a reproducible candidate requiring more non-session-panel examples for independent evaluation.

A Stage A null result may stop expansion only for cells whose Stage A sample is adequate for the declared minimum detectable effect. Underpowered cells remain `INCONCLUSIVE`, not `NO_GO`.

## No-download rule

No Stage A or Stage B market-data request may be executed until the user has seen the exact relevant metadata cost and explicitly authorized the download.
