# XAUUSD Z4 / E-BUY — FIRST_BULL geometry fresh US Aug-2026 validation preregistration v1.0

**Frozen:** 2026-08-27 before any US August-2026 FIRST_BULL reaction outcome is computed or inspected.  
**Scope:** BUY only, US 08:00–17:00 America/New_York.  
**Purpose:** fresh confirmation of the threshold-free bullish-response geometry found in the preregistered H1/H2 study, without replacing the legacy BR70 trigger unless the fresh sample supports the frozen H1 model.

## 1. Frozen location and contact engine

Use unchanged:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

with C5 refresh, sticky top-3, frozen arming/contact/consumption semantics, frozen nearest causal upper-Z4 target and confirmed-M1-close-below-zlo invalidation.

July 2026 may be used only for causal warmup/state leading into August. No July reaction outcome enters this validation.

## 2. Fresh sample

Primary BID source: Dukascopy XAUUSD M1 August 2026 from the same Market-Data-Lab source family used in prior work.

Before outcomes:
- record the raw August CSV SHA-256;
- define eligible sessions mechanically as New-York calendar days for which the raw file contains the full continuous 08:00 through 17:00 US interval needed for the study;
- exclude incomplete edge sessions and days without a complete raw US interval;
- do not choose or drop sessions by reaction result.

The sample is scientifically fresh for this specific FIRST_BULL geometry specification because the prior geometry study used only 2024-08 through 2026-07 and did not open August-2026 US FIRST_BULL outcomes.

## 3. Frozen candidate

`FIRST_BULL` = first confirmed bullish M1 at or after the frozen first-contact bar satisfying only:

`close > open`

No close-position cutoff is used.

Search stops without a candidate if target or invalidation occurs first or if no next-M1 execution can occur before 17:00 NY. Execution reference = next available M1 open.

Outcome and ambiguity semantics remain exactly those in `XAUUSD_Z4_EBUY_BULL_CANDLE_GEOMETRY_PREREG_v1_0_2026-08-27.md`.

## 4. Frozen model — no refit

Use exactly:

`XAUUSD_Z4_EBUY_FIRST_BULL_GEOMETRY_H1_FROZEN_MODEL_v1_0.json`

frozen before August outcomes.

Features, in exact order:
1. close_pos;
2. body_frac;
3. lower_wick_frac;
4. upper_wick_frac;
5. log1p_lower_wick_to_body;
6. range_v.

Use the frozen H1 StandardScaler means/scales and frozen logistic coefficients/intercept. No refit, calibration, feature change or threshold optimization is allowed.

Frozen H1 score cutpoints:
- q20 = `0.2387694161370814`;
- q80 = `0.3273659155086846`.

The frozen H1 close-position-only logistic model in the same artifact is the preregistered reference comparator.

## 5. Primary fresh checks

Report all denominators and bootstrap whole US sessions with seed `20260827`, 1000 draws.

Sample adequacy is `ADEQUATE` only if:
- >=8 complete eligible US sessions;
- >=300 resolved FIRST_BULL observations.

If not, classification is `INSUFFICIENT_FRESH_SAMPLE` and no production conclusion is allowed.

If adequate, `FRESH_GEOMETRY_SIGNAL_PASS` requires both:

1. Frozen H1 6-feature model AUC:
   - point estimate > 0.50;
   - session-bootstrap 95% CI lower bound > 0.50.

2. Frozen score-band ordering:
   - score >= frozen H1 q80 has higher TP1 positive rate than score <= frozen H1 q20;
   - whole-session-bootstrap 95% CI lower bound for `top - bottom` positive-rate difference > 0.

These are the primary confirmation gates.

## 6. Secondary frozen comparisons

Report, without changing the primary gate:
- average precision;
- Brier score and constant-baseline Brier;
- frozen close-position-only AUC and CI;
- 6-feature AUC minus close-position-only AUC and bootstrap CI;
- N and TP1 rate for the legacy descriptive `close_pos >=0.70` subset of FIRST_BULL events;
- N and TP1 rate for q20/middle/q80 frozen geometry-score bands;
- `range_v` univariate AUC and frozen H1-oriented top/bottom quintile effect using the H1 q20/q80 cutpoints recorded from the prior study if available; if exact frozen range_v cutpoints are not present in a pre-outcome artifact, report range_v only as an unthresholded descriptive AUC and do not create fresh-derived cutpoints.

No secondary metric may rescue a failed primary gate.

## 7. Production decision

- PASS: permits a new research cycle to replace the arbitrary BR70 hard cutoff with threshold-free FIRST_BULL plus continuous reaction geometry. It does **not** authorize reusing the old E_BUY_US model, because that model was trained conditional on BR70.
- FAIL: retain BR70 only as the validated legacy trigger for its existing E-score lineage; do not claim 70% is a natural threshold.
- INSUFFICIENT: accumulate a future fresh sample; no replacement decision.

No Pine modification is authorized directly by this fresh geometry test.