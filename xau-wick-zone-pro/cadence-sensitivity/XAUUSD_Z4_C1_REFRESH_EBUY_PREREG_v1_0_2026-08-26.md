# XAUUSD Z4 / E-BUY — C1 minute-refresh sensitivity preregistration v1.0

**Frozen:** 2026-08-26, before any new Aug-2024 → Jul-2026 C1 E-BUY reaction result is generated or inspected.  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** BUY-only, retrospective cadence sensitivity.  
**Production authorization:** NONE.

## 1. Research question

Test whether refreshing the scientific zone state after every completed active M1 bar (`C1`) materially improves the current E-BUY location/reaction process relative to the validated `C5` state, without creating unacceptable zone churn, duplicate contact episodes, causal leakage, or a merely mechanical reaction advantage.

This study is not a visual-redraw study. It changes the scientific state cadence only. The already-decided optional visual-only E-zone envelope remains outside this experiment and must not alter internal zone geometry.

## 2. Frozen detector change

C1 must use the already-audited mechanical cadence candidate:

- frozen source Git blob: `a8a147615c3fd366c49e93b340fd2018b5b66e9e`;
- source cadence literal: `p=utc_ts(ts); return p.minute%15==0 and p.second==0`;
- C1 literal: `p=utc_ts(ts); return p.minute%1==0 and p.second==0`;
- C1 patched SHA-256: `86a5b1af2e77d0e78526652c03f4c6f1a6bfbdaaf92d21e34c1b121f6fdf4dcb`;
- other detector source mutations: `0`;
- lookback: `1440 active M1` unchanged.

No Z4 density, smoothing, peak, boundary, local-band, side, or de-duplication rule may change.

The existing outcome-blind C1/C15 common-timestamp geometry QA is accepted as the detector invariant gate: same landmark row counts, side, center, zlo and zhi within the frozen tolerances, with zero observed mismatch on BID and ASK.

## 3. Frozen E-BUY architecture

Use unchanged:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

with:

- top-3 displayed zones;
- same `0.20v` internal de-duplication tolerance;
- same local band `0 < distance <= 2.0v`;
- no scientific fusion of E1/E2/E3;
- same elapsed-time ESM/EPM/EWM/ESwing parameters.

Only cadence-dependent state transitions are changed from 5 minutes to 1 minute.

## 4. Causal C1 state semantics

A C1 state at timestamp `t` is formed from information known through the completed M1 bar at `t` only. It is usable for contact detection beginning with the next M1 bar; no contact may be assigned to the same bar whose completed information created/updated the state.

For sticky display identity:

- previous-state matching is from the immediately preceding eligible C1 state exactly 1 minute earlier;
- crossed-below checks cover the interval between those two confirmed states;
- carried zones keep priority while still local, not crossed, and matched to a current underlying zone;
- empty slots are filled by the nearest remaining current candidates;
- maximum displayed zones remains three.

A display episode continues only through causal one-step C1 matching. Missing/noncontiguous active minutes break one-step continuity unless explicitly represented by the raw active-M1 chronology; no lineage bridging through unavailable state is allowed.

## 5. Equalized warm-up

The validated C5 E-BUY engine uses 96 C5 landmarks, approximately 480 elapsed minutes. C1 therefore uses **480 C1 landmarks** as the cadence-equivalent warm-up.

The value `96` must not be copied to C1 because that would shorten maturity to about 96 minutes and confound cadence with warm-up.

## 6. Contact / target / invalidation freeze

Use the same E-BUY reaction semantics already frozen for C5, adapted only to the 1-minute state boundary:

- BUY context: New York 08:00–17:00, displayed top-3 E zone below price, at least one causal upper Z4;
- zone must first be ARMED by a confirmed M1 close strictly above its current `zhi`;
- fresh contact is the first subsequent M1 bar whose range overlaps the currently frozen displayed zone;
- max one fresh contact per display episode per US session;
- target at contact = nearest causal upper Z4 known from the C1 state that armed/governed that contact;
- after contact, freeze `center/zlo/zhi`, `v_contact`, and TP1 target for that episode;
- later C1 refreshes must not move that contact's invalidation boundary or target;
- invalidation = first confirmed M1 close strictly below contact-state `zlo`;
- evaluation stops at 17:00 NY same session.

This prevents minute-by-minute recomputation from retrospectively widening/narrowing a live episode.

## 7. Data windows and interpretation status

Use the same frozen Dukascopy BID source/hashes already used by current E-BUY evidence.

- H1: `2024-08-01T00:00:00Z <= t < 2025-08-01T00:00:00Z`;
- H2: `2025-08-01T00:00:00Z <= t < 2026-08-01T00:00:00Z`.

Both periods have been outcome-exposed by prior project work by the freeze date. Therefore this is **retrospective sensitivity**, not pristine OOS validation. Even a favorable C1 result cannot authorize production without later fresh prospective evidence.

## 8. Mandatory C5 control parity

Before interpreting C1, the same study runner must reproduce the frozen source-faithful C5 baseline or consume the exact frozen baseline with provenance guards.

Required baseline anchors:

### H1
- eligible snapshots: `19,878`;
- contact episodes: `16,895`;
- BULL_REJECTION fired: `7,127`;
- TP1 resolved rate: `0.3143902095934731`.

### H2
- eligible snapshots: `20,382`;
- contact episodes: `17,578`;
- BULL_REJECTION fired: `7,643`;
- TP1 resolved rate: `0.3012963205447165`.

No C1 reaction interpretation is allowed if baseline parity fails.

## 9. Primary outcome-blind geometry/stability diagnostics

For C1 and C5, report H1 and H2 separately:

- eligible snapshot count;
- mean/median/p90 displayed-zone count;
- coverage within 1.0v / 1.5v / 2.0v;
- nearest-zone distance median/p90;
- one-step raw display persistence;
- survival-aware persistence;
- `CROSSED_BELOW`, `NO_LONGER_LOCAL`, `UNDERLYING_PRESENT_NOT_DISPLAYED`, `UNEXPLAINED_DISAPPEARANCE` shares;
- native display-episode lifetime in elapsed active minutes (median/p90);
- birth/death rate per 100 eligible state transitions;
- slot-rank churn E1/E2/E3;
- matched consecutive-state center/zlo/zhi drift in `v` units;
- share of C1 updates that materially change the nearest displayed BUY zone;
- runtime/compute burden.

At timestamps divisible by 5 minutes, C1 Z4 detector geometry must remain invariant to C5 geometry within center tolerance `1e-12 USD`, bound tolerance `1e-8 USD`, same side, and same zone count for common eligible timestamps. Any failure is a provenance/engineering failure, not a trading result.

## 10. Primary reaction comparison

Use **BULL_REJECTION only** for the main C1-vs-C5 reaction comparison because it is the current selected trigger and avoids trigger re-selection.

Report H1 and H2 separately:

- fresh contact episodes;
- BR fired count and fired share;
- TP1_FIRST;
- INVALIDATION_FIRST;
- NEITHER;
- AMBIGUOUS / AMBIGUOUS_CONTACT_BAR;
- resolved denominator;
- TP1 resolved rate;
- invalidation resolved rate;
- median/p90 time to TP1 and invalidation when available;
- contact and fired counts per trading day;
- origin-family and US-subperiod diagnostics where denominator is adequate.

Any apparent improvement must be decomposed against changes in contact count, invalidation frequency, target distance, zone width, and episode fragmentation. A higher TP rate caused only by altered episode bookkeeping or a mechanically more permissive invalidation is not evidence of a better cadence.

## 11. Paired uncertainty / coherence rule

Where matching is feasible, use paired trading-day or week blocks to compare C1 versus C5. Report bootstrap 95% intervals for the difference in TP1 resolved rate and key stability metrics.

C1 may be labelled only `PROMISING_RETROSPECTIVE_CADENCE` if all are true:

1. C5 baseline parity passes;
2. detector common-anchor geometry parity passes;
3. direction of the primary reaction difference is coherent in H1 and H2;
4. the improvement is not explained primarily by duplicate/fragmented episodes or altered invalidation geometry;
5. stability/churn remains operationally acceptable;
6. runtime is feasible for Pine/Replay implementation.

Otherwise retain C5.

No numerical minimum TP-rate gain is invented post hoc; effect sizes and intervals are reported. A future promotion threshold, if needed, requires a new precommitted prospective gate.

## 12. Existing E score is excluded from the primary gate

The frozen E model contains cadence-specific semantics, including `episode_age_c5`. Applying it naively to C1 would change the time meaning of an input and is not a valid unchanged-model test.

Therefore:

- E>=80 / E>=90 are **not** primary C1 decision metrics;
- no E model may be refit or recalibrated in this study;
- a later score-transfer or C1-specific E-score study requires a separate preregistration.

This study answers whether the **minute-refreshed zones themselves and their frozen-contact reactions** are better, not whether the old C5 E score can be relabelled C1.

## 13. Pine gate

Do not modify the production Pine to scientific C1 during this study.

Only if C1 is `PROMISING_RETROSPECTIVE_CADENCE` may a separate Pine QA candidate be built. That later gate must include compile, confirmed-bar timing, Replay, runtime, object limits, C1 sticky lineage behavior, and static parameter audit.

## 14. Explicit nonclaims

This study cannot by itself validate:

- profitability after spread/commission/slippage;
- a production C1 E score;
- a new SL/TP/RR;
- actual scientific E-zone fusion;
- FOREXCOM/TradingView feed transfer;
- production replacement of C5;
- prospective statistical validation.