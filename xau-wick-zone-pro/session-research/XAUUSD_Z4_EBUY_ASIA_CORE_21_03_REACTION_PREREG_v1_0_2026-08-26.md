# XAUUSD Z4 / E-BUY — Asia Core 21:00–03:00 NY reaction prereg v1.0

**Frozen:** 2026-08-26, after the fresh August-2026 location/stability holdout PASS and before any Asia-Core BULL_REJECTION / TP1 / invalidation outcome is generated or inspected.

## 1. Question

Test whether the already-authorized **Asia Core 21:00–03:00 NY zone-location layer** also supports the existing causal `BULL_REJECTION` reaction semantics with reaction quality comparable to the current US scientific baseline.

This study does **not** transfer or recalibrate `E_BUY_US`.

## 2. Frozen session and architecture

- session: `21:00 <= America/New_York time < 24:00` OR `00:00 <= time < 03:00`;
- session identity = New York date on which the 21:00 segment begins;
- cadence = **C5**;
- architecture unchanged: `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`;
- top-3 display, `0 < distance <= 2.0v`, sticky v0.4 continuity, de-dup `0.20v`, Z4 priority and 96-C5 warm-up unchanged;
- no E score and no architecture search.

The display state must be built directly with the `21:00–03:00` eligibility filter. No state from `18:00–21:00` may seed the 21:00 session start.

## 3. Reaction engine

Use the project's final repaired pre-outcome chain:

`xau_ebuy_reaction_dev_v1_0_3_final_preoutcome.py`

adapted only for the frozen Asia-Core session boundary and session identity.

Frozen causal semantics:

- BUY zone must be below price and local;
- at least one causal upper Z4 target must exist;
- zone arms on a confirmed close above current `zhi`;
- fresh contact = first later M1 range overlap after arming;
- at most one fresh contact per display episode per Asia-Core session;
- freeze `center/zlo/zhi`, `v_contact` and nearest causal upper-Z4 TP1 at contact;
- `BULL_REJECTION` = bullish candle with close-position >= 0.70 under the final repaired trigger engine;
- execution = next M1 open after the trigger, before 03:00 NY;
- invalidation = first confirmed M1 close strictly below frozen contact `zlo`;
- evaluation ends at 03:00 NY;
- contact-bar ambiguity handling from v1.0.3 remains active;
- no target/invalidation movement after contact.

## 4. Data windows

### Retrospective reaction windows
- H1: `2024-08-01T00:00:00Z <= contact_time < 2025-08-01T00:00:00Z`
- H2: `2025-08-01T00:00:00Z <= contact_time < 2026-08-01T00:00:00Z`

Use the exact frozen Dukascopy BID source manifest/hashes and source-faithful C5 Z4 geometry used by the current E-BUY evidence.

H1/H2 were exposed only for **outcome-blind localization/subperiod diagnostics**; no Asia-Core reaction outcome has been opened before this preregistration.

### Fresh reaction confirmation
Use the exact August-2026 byte stream frozen by the location holdout:
- file `xauusd_bid_m1_2026_08.csv`
- SHA-256 `4f61d531018a8e8c37b1f410945e1d23d59fee96cde13bef223dcc9e63d0f852`

Only complete Asia-Core sessions fully present in that byte stream are eligible. July 2026 is warm-up only.

## 5. Primary reaction metrics

Report separately H1, H2 and Aug-2026 fresh:

- contact episodes and unique episode IDs;
- contacts per Asia-Core session;
- BULL_REJECTION fired count and fired share;
- `TP1_FIRST`, `INVALIDATION_FIRST`, `NEITHER`, ambiguity;
- resolved denominator and resolved share;
- TP1 resolved rate;
- invalidation resolved rate;
- zone width in v;
- target distance in v;
- time to TP1 / invalidation;
- family mix and 21:00–00:00 vs 00:00–03:00 diagnostics.

Also report bootstrap confidence intervals by Asia-Core session for the H1/H2 TP1 resolved rates; they are diagnostic, not post-hoc selection thresholds.

## 6. Frozen transfer gate

The existing US C5 source-faithful TP1-resolved baselines are approximately 31.44% (H1) and 30.13% (H2). Therefore the fixed reaction transfer floor is **30.00% TP1 resolved rate** in each retrospective window.

`ASIA_CORE_BR_REACTION_PASS` requires all of:

1. H1 TP1 resolved rate >= **0.30**;
2. H2 TP1 resolved rate >= **0.30**;
3. H1 resolved share >= **0.90**;
4. H2 resolved share >= **0.90**;
5. no duplicate-contact/session-state bookkeeping failure;
6. no evidence that any apparent advantage is driven primarily by materially shorter TP distance or materially wider invalidation geometry relative to the other retrospective window;
7. fresh August-2026 reaction result is reported without changing the gate. If its denominator is small, it is descriptive rather than a reason to re-optimize H1/H2.

No threshold may be relaxed after outcomes are viewed.

## 7. Authorization

A PASS authorizes **Asia-Core BULL_REJECTION QA markers/alerts without an E score** as a separate session-specific layer. It does not authorize `E_BUY_US` transfer or an `E>=80/E>=90` Asia claim.

A FAIL leaves Asia Core authorized for zones only.

Even a PASS remains retrospective plus partial-month fresh confirmation; production risk/sizing claims are outside scope.