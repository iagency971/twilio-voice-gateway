# E display episode reaction rank V1 — status

**Updated:** 2026-08-29  
**Scope:** XAUUSD M1, BUY, US 08:00–17:00 America/New_York

## Current scientific state

- Canonical outcome-free package: `PASS`
- Second Pro pre-outcome gate: `PASS`
- Current authorization: `GO_DEV_OUTCOME_OPENING`
- Authorized phase: `DEV_HISTORY_ONLY`
- Historical replication outcomes: `CLOSED`
- Prospective outcomes: `CLOSED`
- Production authorization: `NONE`
- Pine modification: `FORBIDDEN`

## Frozen references

- Method commit: `7ef065e209c94e21950c346eed9d4ae0a2d786da`
- Canonical pre-outcome run: `33259414496`
- Canonical artifact: `9716948881`
- Canonical artifact digest: `sha256:62932d000b46a6ad14bdfd8d1d3b47513be0094c72acbfe1028511684b0c707e`
- Additional outcome-blind QA run: `33261123749`
- Additional QA artifact: `9717328401`
- DEV ledger SHA-256: `2cf40bfca54494f1609035307390f3e615348492bf8c853f0c79c63555d060e6`

## Mandatory next checkpoint

The next execution may generate/read DEV labels and fit the single preregistered DEV model only, using `GO_DEV_OUTCOME_OPENING`.

After that execution, DEV labels, model, preprocessing/rank/quartile mapping, report, environment and hashes must be frozen before any historical replication outcome is opened. `GO_HISTORICAL_REPLICATION_DIAGNOSTIC` is not authorized.
