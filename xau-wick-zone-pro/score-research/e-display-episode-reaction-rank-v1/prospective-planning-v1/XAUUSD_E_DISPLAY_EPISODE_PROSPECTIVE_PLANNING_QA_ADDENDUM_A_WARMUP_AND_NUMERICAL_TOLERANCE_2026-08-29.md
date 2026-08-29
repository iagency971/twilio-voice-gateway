# XAUUSD — E V1 prospective planning QA — Addendum A

**Date:** 2026-08-29  
**Phase:** prospective planning only  
**Prospective outcomes generated/read:** NONE  
**Purpose:** close two implementation degrees of freedom exposed by historical dry-run QA before any prospective evidence exists.

## 1. Why this addendum exists

The initial prospective-planning draft stated that the per-session causal archive must contain at least the previous 1,440 active M1 bars. Historical dry-run parity on 2026-07-15 showed that this is sufficient for the frozen Z4 geometry itself, but not for the frozen E evaluation-time population.

The already frozen `xau_ebuy_coverage_v0_1.py` contains both:

- `Z4_LOOKBACK = 1440`; and
- `WARMUP_C5 = 96`.

Its `make_eval_times()` first requires active index `>= 1439` and then discards all evaluation times before the 96th eligible C5 landmark after that lookback. With only 1,440 active pre-session bars, the beginning of the target session is therefore mechanically lost. In the historical dry-run this produced only 35 prospective-style feature rows versus 209 canonical rows.

This discrepancy was discovered and repaired **without generating or reading any prospective reaction outcome**. The repair does not alter any frozen feature, model, geometry, episode, contact or outcome rule.

## 2. Frozen prospective warm-up contract

For every target NY session, the canonical warm-up must begin at the **latest causal active-M1 bar** such that, after the frozen 1,440-active-M1 lookback is satisfied, there are **exactly 96 eligible pre-session C5 landmarks** before the 08:00 New York session open.

Operationally:

1. use only raw bars strictly before the target session open to determine the warm-up start;
2. identify the last 96 pre-session C5 landmarks among active M1 bars;
3. take the earliest of those 96 landmarks;
4. move back exactly 1,439 active M1 positions from that landmark;
5. archive from that active-M1 timestamp through the target session end;
6. fail closed if the required active history or 96 landmarks are unavailable.

The archive manifest must record:

- `frozen_z4_lookback_active_m1 = 1440`;
- `frozen_warmup_c5_landmarks = 96`;
- `eligible_pre_session_c5_landmarks = 96`;
- the selected warm-up start.

This is a causal reproduction of already frozen source semantics, not a new hyperparameter and not a data-dependent optimization.

## 3. Historical dry-run evidence required after this repair

Before the planning package can be sealed, one historical session must simultaneously demonstrate:

- exact Z4 geometry parity against the already frozen historical Z4 artifact;
- Z4 prefix invariance when later bars are appended;
- exact prospective feature-ledger parity against the canonical historical ledger, including row count, timestamps, slot, family, geometry, `v_snapshot`, `zone_width_v` and `display_persistence_c5`;
- exact contact-only parity against the frozen historical reaction-label artifact while reading zero post-contact bars.

No alternate session may be selected because of a failed result. The preselected dry-run session remains 2026-07-15.

## 4. Width-only historical QA numerical tolerance

The width-only comparator is interpretation-only and remains non-gating. The post-replication Pro diagnostic already documented that independent AUC recomputation from serialized artifact floats can differ from the authoritative canonical report by less than `5e-7`.

Therefore the **historical planning-QA cross-check only** is frozen as follows:

- full-model AUC must equal the authoritative `canonical_full_auc` to `1e-12` when the same canonical score field is used;
- independently recomputed width-only AUC may differ from the prior Pro diagnostic width-only AUC by at most `5e-7` absolute;
- the same `5e-7` absolute tolerance applies to a derived full-minus-width value when compared across those two serialization/recomputation paths;
- `gating` must remain `false`;
- `rescue_allowed` must remain `false`.

This `5e-7` tolerance is **not** a prospective scientific pass threshold, is not applied to the primary prospective gate, and cannot change any prospective outcome or model decision. It exists only to recognize the already documented floating-point serialization path in a historical deterministic QA comparison.

## 5. Governance

This addendum is frozen before the prospective start session and before any prospective outcome opening. It must be hashed into the final prospective-planning seal and reviewed at the next Pro pre-prospective-execution gate.

Current authorization remains:

- prospective collection execution: **FORBIDDEN pending Pro gate**;
- prospective reaction outcome generation/reading: **FORBIDDEN**;
- model refit/tuning: **FORBIDDEN**;
- Pine production changes: **FORBIDDEN**.
