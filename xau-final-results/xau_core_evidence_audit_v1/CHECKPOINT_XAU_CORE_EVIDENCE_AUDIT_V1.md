# CHECKPOINT — XAU CORE EVIDENCE AUDIT V1

Date: 2026-08-19

Terminal verdict: **CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION**

## Integrity

- aggregate parity: `True`
- unique core events: `304`
- new market-data spend: `0`
- canonical input rehydration: `true` (same previously used public source/period only)

## RR1.5 descriptive reference

- primary: N=304, mean=0.279918R, PF=1.6470, sum=85.095R
- stress: N=304, mean=0.189605R, PF=1.4084, sum=57.640R

## Frozen Pro gates

- A_integrity: `True`
- B_broad_rr_statistical: `True`
- C_temporal: `True`
- D_concentration: `True`
- E_portfolio: `True`

## Diagnostic dimensions

Direction, contact/entry sessions, DOZ age, DOZ timeframe/variant, objective subtype and session A→B transitions were computed as hypothesis-generation diagnostics only. They do not alter the terminal verdict and may not be used as post-hoc filters in this audit.

See `diagnostic_subgroups.csv`, `zone_age_diagnostics.csv` and `session_transition_diagnostics.csv` for complete tables.
