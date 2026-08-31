# E-zone validity and width-neutral score V2 — status

**Updated:** 2026-08-31  
**Scope:** XAUUSD M1, BUY only, 08:00–17:00 `America/New_York`, displayed E1/E2/E3

## Final state

- R4 targeted Pro neutral-control gate: `PASS`
- Authorized matching design: `R4_D5_MINIMAL_DENSE`
- Sequential R4 execution: `COMPLETE`
- Execution integrity: `PASS`
- Authoritative workflow run: `33334031028`
- Workflow head SHA: `5fe152e250684e35f55236c01cc51fbc9a8fed46`
- PREOUTCOME DEV/VAL/REP: `PASS_AND_FROZEN`
- DEV model fit: `COMPLETE_AND_FROZEN_ONCE`
- Model refit after DEV: `FALSE`
- VAL continuation gate: `FAIL`
- REP outcomes opened: `FALSE`
- Final Pro gate: `COMPLETE`
- Final Pro decision: `NO_GO_PINE_SCORE_NO_STATISTICAL_VALIDATION`
- V2 scientific result: `VALID_NON_CONFIRMATORY_RESULT`
- V2 study status: `CLOSED`
- Production authorization: `NONE`

## Final scientific verdict

- Pooled E zones: `NOT_VALIDATED`
- E1: `NOT_VALIDATED`
- E2: `NOT_VALIDATED`
- E3: `NOT_VALIDATED`
- Width-neutral strength score: `NOT_VALIDATED`
- Pine quality score / strength grading from V2: `NOT_AUTHORIZED`
- Existing visual zones: `EXPLORATORY_ONLY_NOT_STATISTICALLY_VALIDATED`

## Core validation evidence — 2022

### Pooled E-zone test

- Real primary contacts: `18,110`
- Matched real contacts: `10,282`
- Fraction with at least two contacted controls: `56.7753%`, frozen minimum `70%`: `FAIL`
- Matched effect: `+0.0006435` = approximately `+0.064 percentage point`
- 95% bootstrap CI: `[-0.0191901, +0.0193141]`
- One-sided p: `0.488902`
- `pooled_zone_pass`: `FALSE`

Slot effects:

- E1: `-0.0050423`, IC95 `[-0.0285321, +0.0175629]`, `NOT_VALIDATED`
- E2: `+0.0020145`, IC95 `[-0.0246892, +0.0282891]`, `NOT_VALIDATED`
- E3: `+0.0112778`, IC95 `[-0.0240937, +0.0445815]`, `NOT_VALIDATED`

### Frozen width-neutral score

- AUC: `0.507902`
- AUC IC95: `[0.498593, 0.517400]`: `FAIL`
- Q4 minus Q1: `+0.0183238`
- Q4-Q1 IC95: `[-0.0026080, +0.0401730]`: `FAIL`
- Quartile monotonicity: `FAIL`
- Positive Q4-Q1 in fixed width quintiles: `3/5`, required `4/5`: `FAIL`
- Full minus nuisance AUC: `+0.00147846`
- IC95: `[-0.00194148, +0.00496416]`: `FAIL`
- `score_pass`: `FALSE`

Slot score diagnostics:

- E1 AUC: `0.514513`
- E2 AUC: `0.511043`
- E3 AUC: `0.485240`, Q4-Q1 `-0.0532246`

## Sequential closure

The complete frozen validation continuation condition failed. REP 2023 therefore remains sealed and was not opened.

No threshold, feature, model, matching rule, subgroup or gate may be changed within V2 after reading DEV/VAL. No rescue analysis is authorized.

A materially new V3 may only be considered under a separate preregistered outcome-blind protocol before any 2023 outcome is opened.

## Final authorities

- `E_ZONE_SCORE_BUY_US_V2_FINAL_PRO_GATE.json`
- `XAUUSD_E_ZONE_SCORE_BUY_US_V2_FINAL_PRO_GATE_MEMO_2026-08-31.md`
- `R4_FINAL_EXECUTION_RESULT_2026-08-31.json`
- `FINAL_PRO_GATE_REQUEST.json`
- GitHub Actions run `33334031028`
- Final artifact ID `9742754436`
- Final artifact SHA-256 `9612fc99b1a0a61a89f580573952441ab5f0e7fc95e41d422cb20623996a501b`
- DEV frozen model SHA-256 `299728a8bbb2efbb912c225a77eb2725a8cb11d14a03deb6fa6e11e33fe5c9ff`
