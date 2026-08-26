# XAUUSD Z4 — E-BUY fused-zone sensitivity v0.1 — Addendum A: baseline provenance correction

**Frozen:** 2026-08-26, before the corrected sensitivity rerun.  
**Scope:** provenance correction only. This addendum does not change the fusion grid, trigger, model, target rule, endpoint, invalidation rule, feature set, score mapping, or any trading threshold.

## 1. Why this addendum exists

The first fused-zone sensitivity execution was intentionally blocked by the preregistered baseline parity gate because H1 reconstructed `16,895` contact episodes and `7,127` fired `BULL_REJECTION` events instead of the previously published `16,896 / 7,128` H1 reaction counts.

No fused threshold was promoted or interpreted from that failed-parity run.

A targeted provenance audit was then performed before any relaxation of the gate.

## 2. Exact historical provenance audit

The previously published `16,896 / 7,128` H1 reaction evidence came from GitHub Actions run `32908338133`, source commit `a28666a85ddf31d9c999eb7b77d8b2a17f1d2b12`.

That run executed `xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py` and rebuilt E-BUY location state from `xau_ebuy_coverage_v0_4_sticky.py` using a separately reconstructed Z4 geometry (`z4_geometry` SHA-256 `fe5ff37d571af3a2886f39371034eae5395a6af54efbdfe23023355714abcbb5`). It did not consume the frozen OOS E-BUY candidate table as the source of displayed E zones.

The location OOS freeze itself is recorded in `ebuy-coverage-oos-v1-0/XAUUSD_Z4_EBUY_COVERAGE_OOS_REPLICATION_MANIFEST_v1_0.json`. It authorizes `FREEZE_EBUY_LOCATION_ENGINE_AND_AUTHORIZE_REACTION_PREREG` and records the frozen candidate artifact `XAUUSD_Z4_EBUY_OOS_STICKY_CANDIDATES_v1_0.csv.gz` with candidate SHA-256 `157a5f180cc548f51ac9a0fd38ce9e031da48a0dad4fd4170f74b5836d4af90b` and location Z4 geometry SHA-256 `3d3dc4e6948be0f255d714b5c1c34ee21df0ffefe58c91770569ac54b40f034f`.

An exact precomputed-location reaction run (`32909036841`, source commit `cb948d8e852a6e6984c80c6a3189b4f999f087e3`) consumed that frozen OOS candidate table and passed exact aggregate H1 location parity: `19,878` eligible C5 snapshots and `43,511` candidate rows, with all published H1 coverage/count/nearest-distance metrics reproduced to the existing exact tolerances.

That source-faithful run produces:

- H1 contact episodes: `16,895`;
- H1 fired `BULL_REJECTION`: `7,127`;
- H1 `BULL_REJECTION` TP1 resolved rate: `0.3143902095934731`.

The targeted event-level diagnostic also showed that the old `16,896` artifact contains rare identity/geometry pairing differences relative to the frozen candidate table, confirming that forcing one extra contact/BR into the source-faithful baseline would be methodologically wrong.

## 3. Corrected baseline gate for this sensitivity

For the fused-zone sensitivity only, the source-faithful separated-zone H1 baseline is therefore frozen as:

`16,895 contacts / 7,127 fired BULL_REJECTION`.

The H2 baseline gate is unchanged and must continue to reproduce the already-published frozen H2 validation evidence exactly, including contact count, fired BR count, resolved scored N, baseline rate, ROC AUC, AP, E>=80 count/rate and E>=90 count/rate.

This correction is not a threshold relaxation and is not selected from fused outcomes. It is a provenance repair established from the already-frozen location artifact and exact historical workflow audit.

## 4. Parameters explicitly unchanged

The original preregistration remains in force without alteration:

- separated `BASELINE` plus exactly `0.10v, 0.20v, 0.25v, 0.30v, 0.40v, 0.50v` edge-gap fusion thresholds;
- C5 cadence and causal E-BUY state handling;
- `BULL_REJECTION` definition;
- next-M1 execution reference;
- nearest relevant upper-Z4 target rule;
- M1 close below contact-state zlo invalidation;
- 17:00 America/New_York endpoint;
- frozen E_BUY_US logistic model SHA-256 `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`;
- no model refit, no coefficient change, no feature change, no empirical-CDF remap, no trigger or session retuning.

## 5. Interpretation discipline

This remains a retrospective sensitivity study. H1 and H2 are both already outcome-exposed for fusion selection.

A fusion threshold may only be called `PROMISING_RETROSPECTIVE` if its behavior is coherent across H1 and H2 and the apparent benefit is not explained solely by the mechanically wider/lower invalidation boundary created by fusion.

No fusion threshold may be promoted into production or called OOS-validated without fresh untouched/prospective validation.
