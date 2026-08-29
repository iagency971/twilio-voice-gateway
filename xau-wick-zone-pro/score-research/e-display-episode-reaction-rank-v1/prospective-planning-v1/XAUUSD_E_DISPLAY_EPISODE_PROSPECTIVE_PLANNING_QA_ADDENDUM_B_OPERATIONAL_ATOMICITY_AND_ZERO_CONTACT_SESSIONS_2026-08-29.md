# XAUUSD E-display V1 — prospective planning addendum B

**Date:** 2026-08-29  
**Status:** outcome-blind operational clarification frozen before prospective execution  
**Prospective outcomes opened:** NO  
**Model/target/features changed:** NO

## Purpose

This addendum closes operational ambiguities found during the Pro pre-execution review. It does not alter the candidate, reaction target, model, score, quartiles, primary statistical gates or prospective start. It specifies how the already-preregistered first-seen, append-only and represented-session rules must be implemented without silent exclusions or provenance races.

## 1. Atomic upstream source identity

Every collector run must resolve one exact upstream `main` commit before downloading monthly files. Each monthly file must then be downloaded from the raw URL pinned to that exact commit, not from the moving branch name.

For every downloaded file, the collector must record and verify:

- exact upstream commit SHA;
- repository path;
- Git blob SHA computed from the downloaded bytes;
- SHA-256 of the downloaded bytes;
- byte length;
- CSV data-row count;
- collector observation timestamp.

The computed Git blob SHA must equal the contents-API blob SHA at the same exact commit. A mismatch fails closed. This removes the race in which a branch could change between the raw download and metadata request.

## 2. Single collector concurrency

Only one prospective collector run may execute at a time. The installed workflow must use a fixed GitHub Actions concurrency group and `cancel-in-progress: false`. A manual run cannot cancel or overlap a scheduled run.

## 3. First acceptance must survive downstream failure

The canonical first-seen session and warm-up slices, their manifest, and any revision event must be committed to the branch immediately after successful ingestion and before Z4, feature or contact processing.

Therefore, if any later calculation fails, the first observed source bytes remain preserved. The next run must resume from the canonical archive rather than silently replacing it with a later upstream revision.

## 4. Resume rule

The existence of an ingestion manifest is not a reason to skip a session. A session is downstream-complete only when its contact-only manifest exists and passes.

For an incomplete session, the next collector run must:

1. rerun ingestion idempotently against the currently observed exact upstream source;
2. preserve the original canonical session/warm-up bytes;
3. record any genuine source revision append-only;
4. resume Z4, feature and contact processing.

This prevents an ingest-success / downstream-failure state from becoming permanently unprocessable.

## 5. Revision monitoring

Already completed sessions are rechecked only when the Git blob for their calendar month or immediately preceding month changes, because the frozen warm-up can cross the month boundary. An unchanged exact blob does not require reprocessing.

A changed source that produces different canonical session or warm-up bytes is recorded as an append-only revision while the first accepted canonical bytes remain unchanged. Re-observing an already recorded identical revision must not append duplicate revision-chain events.

## 6. Valid zero-zone / zero-candidate / zero-contact sessions

A completed NY session with usable M1 data remains a represented prospective session even if it produces:

- zero qualifying Z4 rows;
- zero displayed E candidates;
- zero model-eligible primary contacts.

Such a session receives successful empty geometry/feature/contact artifacts and contributes one represented session and zero contacts to the stopping rule. It may not be silently excluded or treated as a processing error.

A date with zero usable US-session M1 rows remains unrepresented until usable source data exists, as already preregistered.

## 7. Checkpoint lock contents

The checkpoint lock must include the exact sorted list of represented accepted session dates, in addition to:

- first qualifying end session;
- represented-session count;
- cumulative model-eligible primary-contact count.

The list length must equal the count, begin no earlier than 2026-08-31, and end on the locked checkpoint session. Any drift fails closed.

The three prospective chronological blocks are formed from this exact represented-session list, including valid zero-contact days. Outcome statistics within a block use the contacts belonging to those represented dates.

## 8. Final contact-counter parity before performance opening

At the single checkpoint, the frozen reaction labeler must reproduce exactly the pre-checkpoint contact-only archive before any performance interpretation is accepted.

The final evaluator must verify exact equality for every display episode on:

- selection status;
- first-contact timestamp for primary contacts;
- causally frozen feature-row SHA-256.

The number of model-eligible primary contacts after frozen-model transformation must equal the count written in the checkpoint lock. Any mismatch fails closed.

## 9. Governance

All changes in this addendum are pre-outcome infrastructure hardening. They cannot be used to alter or rescue a prospective result. The following remain unchanged and forbidden:

- model refit or coefficient change;
- feature, target, contact, horizon or ambiguity change;
- rank/quartile recalibration;
- interim performance access;
- production use;
- Pine modification.

A new QA run and a new canonical planning seal are mandatory before the Pro execution gate may issue `GO_PROSPECTIVE_CONFIRMATION_EXECUTION`.
