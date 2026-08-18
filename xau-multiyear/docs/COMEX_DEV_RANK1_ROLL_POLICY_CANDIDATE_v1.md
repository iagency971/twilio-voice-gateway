# COMEX DEV_RANK1 — Causal roll policy candidate v1

Date: 2026-08-18
Status: **CANDIDATE FOR PRO REVIEW — NOT AUTHORIZED FOR PAID ACQUISITION**.

## Problem found by zero-cost QA

A single `GC.v.0` stream is not robust around every GC roll transition. `v.0` ranks contracts by the previous day's trading volume, while `n.0` ranks by the previous day's closing open interest. Both are causal smart-symbol mappings, but they can point to different contracts.

In 96 DEV_RANK1 sessions, the session-start mappings differ on 10 dates. Metadata-only diagnostics show extreme examples where the following session's liquidity migrates strongly away from the prior-day-volume leader. No XAU outcomes were used in this diagnosis.

## Candidate architecture: DUAL when mappings differ

At the canonical GC auction-session start:

1. resolve both `GC.v.0` and `GC.n.0` to raw `instrument_id` using only mappings available at that time;
2. if both resolve to the same raw contract, acquire and use that contract once;
3. if they resolve to different raw contracts, acquire both raw contracts for that selected session;
4. never splice a continuous smart-symbol stream inside a session profile.

### Active contract at an intraday decision timestamp

For any XAU/GC decision occurring after session start:

- compute cumulative traded volume separately for the V0-candidate and N0-candidate raw contracts from canonical GC session start through the **immediately preceding completed minute**;
- choose the contract with greater cumulative volume;
- deterministic tie-break: N0;
- build all local/session-to-date trade-flow and developing-profile features from the selected raw contract only;
- the selection uses no trade after the decision cutoff.

If no completed minute exists yet or both candidates have zero volume, signed-flow/profile features are unavailable for that decision rather than guessed.

### Terminal COMEX-native source zone

For a source level created only after the GC session has completed, the session's full traded volume is already causal. On a divergent-mapping session, the source contract is therefore the candidate with greater **full-session** traded volume; tie-break N0. Terminal VWAP/POC/VAH/VAL/HVN/LVN/voids are generated from that single raw contract.

### Live reproducibility

The same policy can be reproduced live by resolving/subscribing to the two candidate raw contracts at session start and maintaining their cumulative volume. No future mapping or future volume is required for intraday decisions.

## Why not concatenate V0 and N0

Trades from two expiries are never pooled into one volume profile or CVD. Different delivery contracts have distinct price levels and basis. The second contract is a candidate for selection, not an additive source of volume-at-price.

## Paid pilot compatibility

The paid pilot used `GC.v.0`. Among DEV_RANK1 paid sessions, `2013-05-29` has different V0/N0 session-start contracts. Under the dual policy:

- paid V0 tape remains usable as one candidate;
- only the alternate N0 raw contract for that session needs a small top-up purchase;
- the other paid rank-1 sessions can be reused without duplicate purchase when mappings coincide.

## Continuous M1 context

Candidate baseline for continuous context: `GC.n.0 / ohlcv-1m`, because N0's roll mapping is based on previous-close open interest and the zero-cost DEV diagnostics show fewer catastrophic next-session liquidity failures than V0.

For selected sessions, if continuous OHLCV is incomplete, M1 OHLCV is reconstructed deterministically from the chosen raw trade contract. Continuous M1 is not allowed to override selected-session raw tape.

## Alternative for Pro comparison

Simpler alternative: `N0_FROZEN_ONLY` — acquire only the N0 session-start raw contract for every selected session and keep it fixed throughout the session.

The Pro gate should compare the scientific value and extra cost of:

- N0_FROZEN_ONLY;
- DUAL_V0_N0_CAUSAL_ACTIVE.

No paid choice is made by this document.
