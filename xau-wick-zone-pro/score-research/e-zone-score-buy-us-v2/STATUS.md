# E-zone validity and width-neutral score V2 — status

**Updated:** 2026-08-31  
**Scope:** XAUUSD M1, BUY only, 08:00–17:00 `America/New_York`, displayed E1/E2/E3

## Current state

- R4 targeted Pro neutral-control gate: `PASS`
- Authorized matching design: `R4_D5_MINIMAL_DENSE`
- Sequential R4 execution: `COMPLETE`
- Authoritative workflow run: `33334031028`
- Workflow head SHA: `5fe152e250684e35f55236c01cc51fbc9a8fed46`
- PREOUTCOME DEV/VAL/REP: `PASS_AND_FROZEN`
- DEV model fit: `COMPLETE_AND_FROZEN_ONCE`
- Model refit after DEV: `FALSE`
- VAL continuation gate: `FAIL`
- REP outcomes opened: `FALSE`
- Current checkpoint: `READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE_VALIDATION_FAILED_REPLICATION_CLOSED`
- Pine modification: `FORBIDDEN_PENDING_FINAL_PRO_GATE`
- Production authorization: `NONE`

## DEV result — 2020-01-01 to 2022-01-01

### Pooled E-zone validity

- Real primary contacts: `34,144`
- Matched real contacts: `20,962`
- Donor sessions: `514`
- Fraction with at least two contacted controls: `61.3929%` — frozen requirement `>=70%`: **FAIL**
- Matched primary effect: `+0.0105826`
- 95% bootstrap CI: `[-0.0026194, +0.0239762]` — lower bound `>0`: **FAIL**
- One-sided bootstrap p: `0.0575885`
- `pooled_zone_pass`: `FALSE`

### Width-neutral score

- N: `34,144`, sessions: `516`
- Displayed-score AUC: `0.512725`
- AUC 95% CI: `[0.506112, 0.519304]` — **PASS**
- Q4 minus Q1: `+0.0321813`
- Q4-Q1 95% CI: `[+0.0154767, +0.0487506]` — **PASS**
- Full minus nuisance AUC: `+0.00184975`
- 95% CI: `[-0.00040537, +0.00421160]` — lower bound `>0`: **FAIL**
- `score_pass`: `FALSE`

DEV therefore contained a small positive signal, but it did **not** satisfy the complete frozen validity or score gates.

## VAL result — 2022-01-01 to 2023-01-01

### Pooled E-zone validity

- Real primary contacts: `18,110`
- Matched real contacts: `10,282`
- Donor sessions: `258`
- Fraction with at least two contacted controls: `56.7753%` — frozen requirement `>=70%`: **FAIL**
- Matched primary effect: `+0.0006435`
- 95% bootstrap CI: `[-0.0191901, +0.0193141]`
- One-sided bootstrap p: `0.488902`
- `pooled_zone_pass`: `FALSE`

Slot effects:

- E1: `-0.0050423`
- E2: `+0.0020145`
- E3: `+0.0112778`

None passed its frozen slot validation rule.

### Frozen DEV score evaluated without refit

- N: `18,110`, sessions: `258`
- Displayed-score AUC: `0.507902`
- AUC 95% CI: `[0.498593, 0.517400]` — lower bound `>0.5`: **FAIL**
- Q4 minus Q1: `+0.0183238`
- Q4-Q1 95% CI: `[-0.0026080, +0.0401730]` — lower bound `>0`: **FAIL**
- Quartile monotonicity: **FAIL**
- Positive Q4-Q1 in at least 4/5 DEV width quintiles: **FAIL** (`3/5` positive)
- Full minus nuisance AUC: `+0.00147846`
- 95% CI: `[-0.00194148, +0.00496416]` — **FAIL**
- `score_pass`: `FALSE`

Slot AUCs:

- E1: `0.514513`
- E2: `0.511043`
- E3: `0.485240`

## Sequential decision

The complete frozen VAL continuation condition is false because both the pooled zone test and frozen score evaluation fail their predeclared gates.

Therefore:

- `validation_continuation_pass = false`
- `replication_outcomes_opened = false`
- REP 2023 remains sealed by protocol.
- No threshold, feature set, model, matching rule or gate may be altered based on these outcomes.

## Final Pro checkpoint

Return to **Pro** for final scientific adjudication of the completed R4 result.

`READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE_VALIDATION_FAILED_REPLICATION_CLOSED`

Pine remains forbidden until that final Pro gate.

## Final authorities

- `R4_FINAL_EXECUTION_RESULT_2026-08-31.json`
- GitHub Actions run `33334031028`
- Final artifact ID `9742754436`, SHA-256 `9612fc99b1a0a61a89f580573952441ab5f0e7fc95e41d422cb20623996a501b`
- DEV frozen model SHA-256 `299728a8bbb2efbb912c225a77eb2725a8cb11d14a03deb6fa6e11e33fe5c9ff`
