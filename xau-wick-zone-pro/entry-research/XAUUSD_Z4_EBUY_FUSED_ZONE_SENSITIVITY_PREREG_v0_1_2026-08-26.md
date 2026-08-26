# XAUUSD Z4 — E-BUY fused-zone sensitivity preregistration v0.1

**Frozen:** 2026-08-26 before fused-zone outcomes are computed.  
**Scope:** BUY only; retrospective sensitivity, not a new untouched OOS validation. H2 was already opened for the frozen separated-zone architecture before this study.

## 1. Reference architecture

Reference is the already-frozen E-BUY v0.4 top-3 display architecture:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

with the existing C5 cadence, sticky display, causal arming/contact rules, nearest causal upper-Z4 target, `BULL_REJECTION`, M1-close-below-zone invalidation, and same-day 17:00 America/New_York endpoint unchanged.

The frozen `E_BUY_US` M1 logistic model SHA-256 remains:

`ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`

No model refit, coefficient change, feature change, CDF remap, trigger retuning, target change, or session change is permitted in this sensitivity.

## 2. Fusion grid frozen before outcomes

Compare the separated baseline (`BASELINE`) with exactly these edge-gap thresholds in causal snapshot volatility units:

`0.10v, 0.20v, 0.25v, 0.30v, 0.40v, 0.50v`.

At each confirmed C5 snapshot, begin from the existing displayed top-3 E zones, sorted from highest to lowest. Adjacent zones are merged transitively when the edge gap

`gap = current_group_zlo - next_lower_zhi`

satisfies `gap <= threshold * v_snapshot`. Negative gap is overlap and therefore also merges.

For each merged composite:
- `zlo = min(constituent zlo)`;
- `zhi = max(constituent zhi)`;
- `center = (zlo + zhi) / 2`;
- representative `family` = family of the highest constituent zone, deterministic and causal;
- resulting composites are re-ranked high-to-low as slots 1..N.

No unobserved gap is filled beyond the envelope implied by this exact composite definition.

## 3. Reaction and score handling

Each threshold is then run through the same final reaction state machine as the separated reference: episode matching, arming, first contact, one fresh contact per episode/session, nearest frozen upper Z4, BULL_REJECTION, next-M1 execution reference, and 17:00 NY cutoff.

Scientific invalidation remains the first confirmed M1 close strictly below the **contact-state zlo**. Therefore fusion can mechanically lower invalidation by widening the composite. This must be explicitly separated from genuine score discrimination in interpretation.

The frozen E model is applied as-is. Any E performance under fusion is diagnostic under shifted feature distributions, not a newly calibrated score.

## 4. Windows

Report separately:
- H1: 2024-08-01 <= t < 2025-08-01 UTC;
- H2: 2025-08-01 <= t < 2026-08-01 UTC.

Both are retrospective for fusion selection because H2 is already spent.

## 5. Frozen outputs

For BASELINE and every fusion threshold, report per H1/H2:
- eligible C5 snapshots;
- mean, median and p90 displayed-zone count;
- share of snapshots whose displayed-zone count is reduced vs baseline;
- median and p90 zone/composite width in `v` units;
- coverage within 1.0v, 1.5v and 2.0v where available;
- contact episode count;
- BULL_REJECTION fired count/share;
- resolved `TP1_FIRST`, `INVALIDATION_FIRST`, `NEITHER`, ambiguity and TP1 resolved rate;
- frozen-score resolved N, baseline positive rate, ROC AUC, average precision;
- E>=80 count/positive rate;
- E>=90 count/positive rate.

Also report deltas versus BASELINE, especially zone-count reduction, width inflation, invalidation-first reduction, and score-band performance.

## 6. Baseline parity gate

The BASELINE run must reproduce the published separated-zone architecture before fused results are interpreted. At minimum H1 contact/BULL_REJECTION counts and H2 published validation counts/metrics must match the frozen evidence within exact or explicitly documented numeric tolerance. If baseline parity fails, fused results are `NO_INTERPRETATION_PARITY_FAIL`.

## 7. Decision discipline

This is a sensitivity study. A threshold may be labelled `PROMISING_RETROSPECTIVE` only if improvements are coherent across H1 and H2 and are not explained solely by a much lower/wider invalidation boundary.

No fusion threshold may be promoted into the production Pine or called OOS-validated from this study alone. Any chosen fusion rule must be frozen and validated on fresh untouched/prospective data before replacing the separated-zone architecture.
