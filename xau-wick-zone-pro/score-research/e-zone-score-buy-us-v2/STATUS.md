# E-zone validity and width-neutral score V2 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY only, 08:00–17:00 `America/New_York`, displayed E1/E2/E3

## Current state

- Targeted Pro methodological gate: `PASS`
- Decision: `GO_E_ZONE_SCORE_BUY_US_V2_SEQUENTIAL_HISTORICAL_EXECUTION`
- Exact study scope: `M1 / BUY / US / E1-E2-E3`
- SELL: `EXCLUDED`
- Other sessions: `EXCLUDED`
- Other timeframes: `EXCLUDED`
- Existing V1 prospective stream: `SEPARATE_NONBLOCKING`
- V2 historical outcome execution: `AUTHORIZED`
- Pine modification: `FORBIDDEN_PENDING_FINAL_PRO_GATE`
- Production authorization: `NONE`

## What V2 must decide

1. Do displayed E zones outperform matched neutral placebo levels after contact?
2. Is the pooled E-zone effect valid?
3. Are E1, E2 and E3 each valid under their own multiplicity-adjusted gate?
4. Does a score made only from causal evidence, persistence, confluence, stability and family add predictive rank beyond width, distance, slot and market context?
5. Is the score sufficiently width-neutral to justify a 0–100 display?

## Frozen correction to V1

The V1 historical rank remains reproducible, but it is not accepted as the final zone-quality score because:

- its target/adverse construction rewarded wider zones mechanically;
- its score was correlated at approximately 0.995 with its width component;
- the model added only about 0.00143 AUC over width in DEV and 0.00073 in replication.

V2 therefore uses a symmetric outcome around the contact-bar close and removes every width/location/context contribution from the displayed score.

## Frozen windows

- DEV: `2020-01-01 <= contact < 2022-01-01`
- Validation: `2022-01-01 <= contact < 2023-01-01`
- Replication: `2023-01-01 <= contact < 2024-01-01`
- Non-gating robustness only: `2024-01-01 <= contact < 2024-08-01`
- Known V1 interval 2024-08 through 2026-07: forbidden for V2 fitting or tuning

## Execution contract

Très élevé must carry out the complete sequential workflow without an intermediate user handoff or intermediate Pro gate. Replication may be opened only if the frozen validation continuation gate passes. If validation fails, the final package must be produced with replication closed.

## Next checkpoint

`READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE`

or, if the mechanical validation continuation gate fails:

`READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE_VALIDATION_FAILED_REPLICATION_CLOSED`

The final Pro gate will adjudicate pooled E, E1, E2, E3 and the V2 width-neutral score separately. Only a final score PASS may authorize a Pine formula.
