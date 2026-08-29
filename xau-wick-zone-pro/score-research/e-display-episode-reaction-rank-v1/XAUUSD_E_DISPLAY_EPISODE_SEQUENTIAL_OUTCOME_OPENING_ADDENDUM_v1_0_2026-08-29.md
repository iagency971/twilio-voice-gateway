# XAUUSD — E display episode V1 — sequential outcome opening addendum

**Frozen date:** 2026-08-29  
**Scope:** XAUUSD M1, BUY only, US 08:00–17:00 America/New_York  
**Outcome access at freeze:** FORBIDDEN

## Purpose

This addendum closes a pre-outcome sequencing ambiguity before any real reaction labels are generated or read.

## Mandatory opening sequence

Real historical outcomes may never be opened for DEV and historical replication in the same execution.

### Phase 1 — DEV only

The only token permitted for the first real-label phase is `GO_DEV_OUTCOME_OPENING`.

That phase may:

1. label only episodes whose primary contact belongs to the declared DEV window;
2. fit the single preregistered logistic model on DEV primary contacts only;
3. freeze preprocessing statistics, categorical vocabulary, coefficients, intercept, DEV score distribution, empirical-rank mapping and quartile cutpoints;
4. write DEV evaluation evidence.

That phase must not read, label, load, score or summarize any historical-replication price outcome.

### Intermediate freeze

After DEV, a separate frozen model artifact and manifest must be committed/hashed before any historical replication outcome is opened.

No model feature, coefficient, transform, threshold, rank mapping, quartile rule, bootstrap rule or gate may change after reading DEV unless the candidate is abandoned and a newly preregistered research cycle begins.

### Phase 2 — historical replication diagnostic only

Historical replication may be opened only under a distinct token: `GO_HISTORICAL_REPLICATION_DIAGNOSTIC` and only with a previously frozen DEV model artifact.

The replication phase may not refit or alter the model. It may only apply the frozen DEV transform/model/rank/quartile mapping and report the preregistered diagnostics.

Historical replication remains diagnostic and cannot authorize production.

## Contact-time window authority

Window membership for any labeled primary observation is determined by `contact_bar_open_time_utc`, not by snapshot time alone.

DEV:

`2024-08-01T00:00:00Z <= contact_bar_open_time_utc < 2025-08-01T00:00:00Z`

Historical replication diagnostic:

`2025-08-01T00:00:00Z <= contact_bar_open_time_utc < 2026-08-01T00:00:00Z`

Any label generated from a ledger split whose eventual contact falls outside its declared window must fail closed.

## Pre-outcome status

No real label is generated or read by this addendum. The second Pro pre-outcome gate remains required before `GO_DEV_OUTCOME_OPENING` can be supplied.
