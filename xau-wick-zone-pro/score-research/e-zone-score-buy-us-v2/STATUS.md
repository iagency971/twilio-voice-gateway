# E-zone validity and width-neutral score V2 — status

**Updated:** 2026-08-30  
**Scope:** XAUUSD M1, BUY only, 08:00–17:00 `America/New_York`, displayed E1/E2/E3

## Current state

- Original targeted Pro V2 gate: `PASS`
- R4 targeted Pro neutral-control gate: `PASS`
- Current decision: `GO_R4`
- Authorized matching design: `R4_D5_MINIMAL_DENSE`
- Outcome-blind status: `NO_V2_FUTURE_REACTION_OUTCOME_OPENED`
- Current execution state: `R4_PREOUTCOME_IMPLEMENTATION_AND_REBUILD_REQUIRED`
- Old R2 execution authorization: `SUPERSEDED_FOR_NEW_EXECUTION`
- New outcome-execution token after complete R4 PREOUTCOME PASS: `GO_E_ZONE_SCORE_BUY_US_V2_R4_SEQUENTIAL_HISTORICAL_EXECUTION`
- Pine modification: `FORBIDDEN_PENDING_FINAL_PRO_GATE`
- Production authorization: `NONE`

## R4 methodological verdict

`R4_D5_MINIMAL_DENSE` is scientifically authorized with the exact frozen parameters and without any fallback to D6-D8.

The predeclared outcome-blind Pro diagnostics passed on the 2022 design population:

- donors with at least two controls: `82.2393278069%`;
- minimum slot-specific coverage: `80.4101035902%`;
- donor-equal max absolute SMD: `0.0822776729`;
- donor-equal max weighted KS: `0.0805247940`;
- max soft-categorical total-variation distance: `0.0433080765`;
- eligible donors with two controls retaining at least half the donor path: `97.0000342853%`.

The exact V0.4 overlap parity has also been reproduced on `88,557 / 88,557` rows with zero mismatch and zero maximum delta. Exact parity remains fail-closed.

## Mandatory work before any outcome

1. Implement the exact R4 placebo generator, runner and QA.
2. Supersede the R2-only caliper assertions and authorization path.
3. Rebuild complete outcome-blind DEV, VAL and REP packages.
4. Pass every fixed R4 coverage, donor-equal balance, distributional, categorical, path-support, neutrality, determinism, prefix-invariance and exact-parity gate in every window.
5. Freeze and hash the complete PREOUTCOME package before generating any reaction label.

If every PREOUTCOME requirement passes, DEV may be opened without another Pro gate. If any requirement fails, stop before DEV and return to Pro.

## Frozen windows and sequential rule

- DEV: `2020-01-01 <= contact < 2022-01-01`
- Validation: `2022-01-01 <= contact < 2023-01-01`
- Replication: `2023-01-01 <= contact < 2024-01-01`
- Non-gating robustness only: `2024-01-01 <= contact < 2024-08-01`
- Known V1 interval 2024-08 through 2026-07: forbidden for V2 fitting or tuning

Fit the model exactly once on DEV. Evaluate VAL without refit. Open REP only if the complete frozen VAL continuation gate passes.

## Authorities

- `E_ZONE_SCORE_BUY_US_V2_R4_PRO_GATE.json`
- `XAUUSD_E_ZONE_SCORE_BUY_US_R4_PRO_GATE_MEMO_2026-08-30.md`
- `R4_PRO_AUDIT_PREDECLARED_DIAGNOSTIC_GATES_2026-08-30.json`
- `R4_PRO_AUDIT_DIAGNOSTICS_VAL_2026-08-30.json`
- `R4_PRO_AUDIT_GATE_RESULT_2026-08-30.json`
- `V04_PARITY_REPRODUCIBILITY_DIAGNOSTIC_2026-08-30.json`

## Next Pro checkpoint

`READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE`

or, if the mechanical VAL continuation gate fails:

`READY_FOR_PRO_E_ZONE_SCORE_BUY_US_V2_FINAL_GATE_VALIDATION_FAILED_REPLICATION_CLOSED`
