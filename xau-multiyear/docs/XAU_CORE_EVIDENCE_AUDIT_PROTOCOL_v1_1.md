# XAU CORE EVIDENCE AUDIT PROTOCOL v1.1

Date frozen: 2026-08-19  
Execution branch: `agent/xau-core-evidence-audit-v1`  
Authority: actual Pro decision at commit `70ac8036a67af44ac613fad327b4911d7a191600` on `agent/xau-comex-acquisition-plan`  
Supersedes for execution details only: `XAU_CORE_EVIDENCE_AUDIT_PROTOCOL_v1.md`  
Status: `FROZEN_BEFORE_CORE_LEDGER_AND_AUDIT_METRICS`

## 1. Scope unchanged from Pro

Execute only `XAU_CORE_EVIDENCE_AUDIT_V1` on the already-known 2011–2025 historical candidate:

`DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL`

No signal, zone, behavior, entry, stop, horizon, RR, cost model or session/direction filter may be changed.

This protocol does **not** authorize M5, COMEX continuation outcomes, a new provider, a new historical period, parameter search, live deployment or a prop-firm challenge.

## 2. Canonical baseline binding

Historical result branch: `agent/xau-multiyear-research`.

Canonical bindings inherited from Pro:

- annual runner source commit: `6efa3789458a6584054fb3ee923dfccca2e15e9d`;
- multiyear manifest blob: `b82e0835355ff322e0c645c35ddd8f6776be5e6d`;
- survivors blob: `8f80031ccc0a2e6ab48b32a154cfd76387295ca3`;
- original Vantage runner blob: `ac99a1be6dd4b8638b176192809b2a23978fd70a`;
- entries v1 blob: `cf3dedabd70d303adb3d74b2ee585a1e5745d7a7`;
- entries v2 blob: `f5365c11020a5225fce152e4ed262fc7f919026c`;
- stacking blob: `d1ffcbe88bdf65da61ed873a9390a5bdf66e7049`;
- config blob: `6704dd595aa45973cb8a1752d98d8daf77d83eaf`;
- zones blob: `07f113ab35994bd19e3b970cefce15e93b304fcc`.

Frozen core:

- DOZ timeframes: `15min / 30min / 1h`;
- target surface: `0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0 R`;
- horizon: 120 minutes;
- scenarios: `S10_C6`, `S11_C6_PRIMARY`, `S12_C6`, `S18_C9_STRESS`;
- RR1.5 is descriptive only and may not be selected as a winner.

## 3. Canonical input rehydration clarification

The 2011–2025 annual workflows did not persist their raw merged Dukascopy input files; they persisted only annual summaries/manifests. Therefore a trade ledger cannot be reconstructed from repository artifacts alone.

For this audit only, **canonical input rehydration** is permitted as an execution necessity under all of the following hard restrictions:

1. use the same public monthly BID/ASK source URLs and the same merge semantics as `xau-multiyear/scripts/acquire_dukascopy_window.py`;
2. use exactly the same historical target years 2011–2025 and the same annual warm-up/post-window construction as the frozen Vantage workflow;
3. no new provider, schema, timeframe, calendar period or market information may be added;
4. new market-data spend must remain exactly zero;
5. hash every rehydrated annual merged input;
6. the historical aggregate parity gate is mandatory and fail-closed. Any material mismatch gives `CORE_RESULT_INVALID_REPAIR_REQUIRED` and stops the audit.

This is a deterministic replay of the already-used research input, not an extension of the research sample. The audit must disclose `canonical_input_rehydration=true` and `new_research_market_information=false`.

## 4. Mandatory trade ledger

Persist one row per core event × scenario × RR with, at minimum:

- stable `event_id`, `stack_id`, representative `zone_id`;
- source year and 17:00-New-York trading date;
- contact, confirmation, entry and exit timestamps and indices;
- direction (`LONG`/`SHORT`);
- representative zone lower/upper/centre;
- constituent zone IDs, families and variants;
- deterministic DOZ anchor and objective-liquidity anchor;
- DOZ source timeframe(s), variants, origin/known timestamps;
- objective-liquidity variants and origin/known timestamps;
- entry, stop, target and exit prices;
- structural risk, spread, commission;
- gross R, net R, result, ambiguity flag;
- concurrent open-position count;
- input and code provenance.

The ledger must be hashed before inferential summaries are produced.

## 5. Outcome-blind diagnostic enrichment requested before execution

The following dimensions are frozen as **diagnostics only**. They may explain heterogeneity and generate later hypotheses, but no subgroup may rescue a failing aggregate or become a live filter in this audit.

### 5.1 Direction

- `LONG` versus `SHORT`.

### 5.2 Trade/contact sessions

Using the existing `America/New_York` session buckets:

- `ASIA_CME`: 18:00–02:59;
- `LONDON`: 03:00–07:59;
- `NY_AM`: 08:00–11:59;
- `NY_PM`: 12:00–15:59;
- `TRANSITION`: 16:00–17:59.

Report contact session, confirmation session, entry session and exit session separately.

### 5.3 DOZ anchor definition

For each stacked core event, gather all constituent `DISPLACEMENT_ORIGIN` zones. Choose one deterministic diagnostic anchor by sorting on:

1. smallest zone width;
2. earliest `known_time`;
3. earliest `origin_time`;
4. lexical `zone_id`.

No outcome may influence this choice.

Also persist the complete constituent DOZ list so the anchor can be audited.

### 5.4 Objective-liquidity anchor definition

Among `OBJECTIVE_LIQUIDITY` constituents use the same deterministic ordering: width, known time, origin time, zone ID. Persist the complete objective constituent list.

### 5.5 Zone age

For the deterministic DOZ anchor calculate:

- structural age: `contact_time - origin_time`;
- tradable age: `contact_time - known_time`;
- entry tradable age: `entry_time - known_time`;
- age in source-timeframe bars: tradable-age minutes divided by source-timeframe minutes.

Fixed descriptive tradable-age buckets, frozen before outcomes:

- `<1h`;
- `1-4h`;
- `4-12h`;
- `12-24h`;
- `1-3d`;
- `3-7d`;
- `7-30d`;
- `>=30d`.

Also report continuous age distributions and quartiles. Buckets are not selection gates.

### 5.6 Session A → session B matrices

For the DOZ anchor compute and report, at minimum:

- origin session → contact session;
- activation/known session → contact session;
- activation/known session → entry session;
- origin session → entry session.

For objective-liquidity constituents also report objective activation session → contact/entry session when defined.

### 5.7 Timeframe and objective subtype

Report diagnostic performance by:

- DOZ source timeframe `15min`, `30min`, `1h`;
- DOZ variant `DOZ_LAST`, `DOZ_BODY`, `DOZ_BASE`;
- objective-liquidity subtype/variant;
- combinations only when sample size is disclosed.

No combination may be promoted in V1.1.

## 6. Hard parity gate

Before any inference or subgroup profitability table:

1. reproduce exactly 304 underlying core entry events across 2011–2025;
2. all six RR cells in the primary scenario must use exactly the same 304 event IDs;
3. all four cost scenarios must use the same event IDs;
4. reproduce the published multiyear aggregates within floating-point tolerance;
5. fail on duplicate/untraceable event IDs;
6. audit-specific enriched stack construction must reproduce canonical stack representatives and constituent family/variant summaries exactly.

Failure verdict: `CORE_RESULT_INVALID_REPAIR_REQUIRED`. Stop before inferential/subgroup interpretation.

## 7. Frozen inference and robustness

Primary statistical unit: 17:00-New-York trading date.

- date-cluster bootstrap: 20,000, seed `20260821`;
- three-month moving-block bootstrap of monthly aggregate R: 20,000, seed `20260822`;
- leave-one-year-out recomputation;
- annual contribution shares;
- best 1/5/10% contribution;
- expectancy after removing best 5%;
- max drawdown and longest losing streak;
- concurrency diagnostics;
- single-position replay using earliest entry, then contact time, then stable event ID; later entries are ignored until exit.

Pro pass/fail gates remain exactly those frozen in the actual Pro memo. Diagnostic session/direction/age/A→B tables do not participate in the pass/fail decision.

## 8. Terminal verdicts

Only:

- `CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION`;
- `CORE_RESULT_INVALID_REPAIR_REQUIRED`;
- `CORE_HISTORICAL_CANDIDATE_NO_GO_FOR_EXTERNAL_REPLICATION`.

After the terminal verdict, stop. Do not launch M5, rejected-strategy subgroup rescue, COMEX continuation, new market-data purchases or a prop challenge in the same workflow.