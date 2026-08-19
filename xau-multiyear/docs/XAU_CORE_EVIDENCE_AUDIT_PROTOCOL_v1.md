# XAU CORE EVIDENCE AUDIT PROTOCOL v1

Date frozen: 2026-08-19  
Authority: `PRO_DECISION_MEMO_XAU_CORE_VALIDATION_FIRST_2026-08-19.md`  
Status: `FROZEN_BEFORE_CORE_LEDGER_AND_AUDIT_METRICS`  
Authorized execution mode: `TRES_ELEVE`

## 1. Purpose

Execute only `XAU_CORE_EVIDENCE_AUDIT_V1` for the already-known 304-trade historical core.

This protocol does not authorize:

- M5 or any other new zone timeframe;
- new COMEX outcomes;
- new market-data acquisition;
- parameter optimization;
- live or prop-firm deployment.

## 2. Canonical baseline binding

Historical result branch:

`agent/xau-multiyear-research`

Annual runner source commit recorded in the canonical multiyear manifest:

`6efa3789458a6584054fb3ee923dfccca2e15e9d`

Canonical artifact bindings:

- `xau-final-results/phase_c_vantage_raw_2011_2025/manifest.json`
  - Git blob SHA: `b82e0835355ff322e0c645c35ddd8f6776be5e6d`
  - declared surface cells: 210
  - declared survivors: 8
- `xau-final-results/phase_c_vantage_raw_2011_2025/survivors.csv`
  - Git blob SHA: `8f80031ccc0a2e6ab48b32a154cfd76387295ca3`
- `xau-multiyear/scripts/run_phase_c_vantage_raw.py`
  - Git blob SHA: `ac99a1be6dd4b8638b176192809b2a23978fd70a`
- `xau-multiyear/src/rzr/entries_v1.py`
  - Git blob SHA: `cf3dedabd70d303adb3d74b2ee585a1e5745d7a7`
- `xau-multiyear/src/rzr/entries_v2.py`
  - Git blob SHA: `f5365c11020a5225fce152e4ed262fc7f919026c`
- `xau-multiyear/src/rzr/stacking.py`
  - Git blob SHA: `d1ffcbe88bdf65da61ed873a9390a5bdf66e7049`
- `xau-multiyear/src/rzr/config.py`
  - Git blob SHA: `6704dd595aa45973cb8a1752d98d8daf77d83eaf`
- `xau-multiyear/src/rzr/zones.py`
  - Git blob SHA: `07f113ab35994bd19e3b970cefce15e93b304fcc`

The audit implementation may add persistence and diagnostics, but it may not alter the bound signal, behavior, entry, stop, horizon, RR or cost semantics.

## 3. Frozen core

- sample: `DOZ_OBJECTIVE_ONLY`
- entry model: `CLEAN_REJECTION`
- risk rule: `STRUCTURAL`
- DOZ timeframes: `15min`, `30min`, `1h`
- horizon: 120 minutes
- RR surface: 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0
- execution scenarios: `S10_C6`, `S11_C6_PRIMARY`, `S12_C6`, `S18_C9_STRESS`
- descriptive reference RR: 1.5 only

## 4. Required output directory

`xau-final-results/xau_core_evidence_audit_v1/`

Required artifacts:

1. `core_trade_ledger.csv`
2. `ledger_manifest.json`
3. `aggregate_parity_report.json`
4. `rr_surface_inference.csv`
5. `date_cluster_bootstrap_summary.csv`
6. `moving_block_bootstrap_summary.csv`
7. `leave_one_year_out.csv`
8. `annual_contribution.csv`
9. `concentration_stress.csv`
10. `drawdown_losing_streak.csv`
11. `concurrency_report.json`
12. `single_position_replay.csv`
13. `diagnostic_subgroups.csv`
14. `audit_verdict.json`
15. `SHA256SUMS`
16. `CHECKPOINT_XAU_CORE_EVIDENCE_AUDIT_V1.md`

## 5. Required ledger fields

At minimum:

- stable event and stack IDs;
- source year and trading date;
- contact, confirmation, entry and exit timestamps/indices;
- direction;
- zone geometry;
- constituent families/variants;
- DOZ timeframe(s);
- objective subtype(s);
- entry/stop/target/exit prices;
- structural risk;
- spread/commission;
- gross/net R;
- result and ambiguity flag;
- concurrent-position count;
- input/code provenance.

## 6. Hard execution order

1. Reconstruct ledger.
2. Hash ledger and write `ledger_manifest.json`.
3. Run parity assertions.
4. If parity fails, write only repair diagnostics and verdict `CORE_RESULT_INVALID_REPAIR_REQUIRED`; do not continue inference.
5. If parity passes, compute the frozen inference, concentration and concurrency outputs.
6. Write the final machine-readable verdict using the decision mapping in the Pro memo.
7. Stop. Do not launch external replication, M5 or COMEX continuation.

## 7. Seeds

- date-cluster bootstrap: 20,000, seed `20260821`
- three-month moving-block bootstrap: 20,000, seed `20260822`

## 8. No-rescue rule

Results by direction, session, timeframe or objective subtype are diagnostic only.

A failing aggregate may not be rescued by:

- choosing a subgroup;
- choosing one RR;
- changing a stop or horizon;
- adding a trend/session/FVG/COMEX filter;
- changing the cost model;
- opening M5.

## 9. Valid terminal verdicts

- `CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION`
- `CORE_RESULT_INVALID_REPAIR_REQUIRED`
- `CORE_HISTORICAL_CANDIDATE_NO_GO_FOR_EXTERNAL_REPLICATION`

No other terminal verdict is authorized.
