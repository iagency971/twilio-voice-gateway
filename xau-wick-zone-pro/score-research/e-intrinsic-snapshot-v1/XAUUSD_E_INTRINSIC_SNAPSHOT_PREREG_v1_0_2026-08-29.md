# XAUUSD — E_INTRINSIC_SNAPSHOT_V1 — preregistration outcome-blind

**Frozen date:** 2026-08-29  
**Repository:** `iagency971/twilio-voice-gateway`  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** XAUUSD M1, BUY only, US 08:00–17:00 `America/New_York`  
**Production authorization:** NONE  
**Outcome access:** FORBIDDEN until the Pro pre-outcome gate.

## 1. Purpose

This preregistration implements the outcome-blind methodological audit of the E score. The object is not a trading score. It is a causal historical ledger of the information intrinsically observable for each displayed E episode before any later contact/reaction is used.

The frozen E localization architecture is not recalibrated:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`, maximum three sticky displayed zones.

The canonical v0.4 displayed-candidate source is:

`xau-wick-zone-pro/entry-research/ebuy-coverage-v0-4/XAUUSD_Z4_EBUY_STICKY_CANDIDATES_v0_4.csv.gz`

Expected SHA-256 from the frozen v0.4 manifest:

`dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920`

## 2. Scientific unit

The ledger unit is **one displayed E episode at one confirmed C5 snapshot**. A future reaction study will reduce this repeated-snapshot ledger to **one episode per NY session at the first armed contact**, using only the last snapshot strictly before that contact.

E1/E2/E3 is not an episode identity and is not a quality rank.

## 3. Episode identity

Snapshots are contiguous only when separated by exactly five minutes. Across any larger gap, including overnight/session gaps, identity is reset.

For a current zone and an unused prior zone, identity may continue if:

`overlap([zlo_old,zhi_old],[zlo_new,zhi_new])`

OR

`abs(center_old-center_new) <= 0.25 * max(v_old,v_new)`.

Matching is one-to-one. Current zones are processed in display-slot order only for deterministic resolution. Among valid unused prior matches, select minimum absolute center distance, then smallest prior episode sequence as tie-break.

A slot change does not create a new episode. A family-label change does not create a new episode if the geometric identity rule still matches. The origin family remains the family at episode birth.

## 4. Causal timing

Every ledger row is computed solely from the frozen v0.4 candidate row at that snapshot and prior ledger state. No future candle, future contact, future rejection, target, MFE/MAE, trade result or future Z4 state is used.

The ledger is expected to satisfy prefix invariance: rebuilding on any historical prefix must reproduce exactly the same identities and model features for that prefix as rebuilding on the full dataset.

## 5. V1 model-feature whitelist

Only four fields are eligible for a future intrinsic reaction model:

1. `zone_width_v` = `(zhi-zlo)/v_snapshot`;
2. `episode_age_c5` = number of contiguous confirmed C5 snapshots in the episode, starting at 1;
3. `current_family` = frozen v0.4 family label at the snapshot;
4. `origin_family` = family label at episode birth.

No scalar score is created at this stage.

**Intrinsic-model eligibility:** a future model row is eligible only when both `current_family != Z4` and `origin_family != Z4`. Z4-origin/current rows remain in the ledger for completeness and separate structural analysis, but cannot train the intrinsic E score.

### Important restraint

The audit identified potentially interesting concepts such as independent evidence count, freshness, density concentration and family diversity. The canonical v0.4 displayed-candidate ledger does not preserve enough provenance to reconstruct those quantities without changing/re-instrumenting the generators. V1 therefore does **not** invent them retrospectively. Any such V2 feature requires a new outcome-blind specification and generator instrumentation before outcomes are consulted.

## 6. Metadata / QA-only fields

The following are retained for identity, reproducibility and QA but are excluded from the future intrinsic model:

- `episode_id`, `episode_seq`;
- `snapshot_time_utc`, `session_date_ny`;
- `display_slot_rank`;
- raw `center`, `zlo`, `zhi`, `v_snapshot`;
- `is_new_episode`;
- previous snapshot and slot metadata;
- `family_changed`;
- one-step center/boundary shifts;
- `row_sha256`.

The one-step shifts are recorded only to audit temporal stability/repaint. They are not model features in V1.

## 7. Explicitly excluded context

The following fields present or derivable from the v0.4 coverage ledger cannot enter `E_INTRINSIC_SNAPSHOT_V1` model features:

- display rank / E1 E2 E3;
- current market close and distance-to-price;
- `upper_z4_count`;
- distance to upper Z4 / target geometry;
- any session subperiod feature;
- approach trend or volatility regime beyond mechanical normalization;
- contact, penetration, rejection or execution features.

Z4 geometry remains a separate future block named `Z4_CONTEXT`.

## 8. Forbidden outcome fields

The pipeline must fail closed if candidate input contains outcome-like fields, including TP/SL, MFE/MAE, W5/W15/W30/W60, success/reaction labels, invalidation, P&L, expectancy, return or future-outcome columns.

## 9. Determinism and hashes

The output CSV is compressed deterministically with gzip `mtime=0`. Each row receives a deterministic SHA-256 over canonicalized pre-hash fields. The artifact manifest includes source and ledger SHA-256.

## 10. Required QA before outcome opening

All checks must pass:

- exact source SHA-256;
- row count parity with US rows of the frozen candidate source;
- no more than three rows per snapshot;
- unique display slot per snapshot;
- valid zone geometry and positive `v_snapshot`;
- all rows inside US 08:00–17:00 New York;
- stable origin family per episode;
- one NY session per episode;
- age starts at 1 and increments by 1;
- independent reimplementation of identity matches the ledger;
- prefix invariance / no-repaint;
- row hashes independently recompute;
- no forbidden output columns;
- model feature whitelist is exact.

Failure of any check sets authorization to `BLOCK_OUTCOME_OPENING`.

## 11. What this preregistration does NOT claim

It does not claim that E zones react, that any feature is predictive, that an intrinsic score exists, that E1 is stronger than E2/E3, or that a BUY strategy is profitable.
