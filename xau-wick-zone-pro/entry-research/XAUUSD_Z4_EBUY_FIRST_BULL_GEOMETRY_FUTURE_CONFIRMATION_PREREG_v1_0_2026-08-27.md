# XAUUSD Z4 / E-BUY — FIRST_BULL geometry future confirmation preregistration v1.0

**Frozen:** 2026-08-27 after the partial fresh Aug-2026 confirmation failed its uncertainty gates and before any XAUUSD US reaction outcome strictly later than the already-opened source cutoff is used for this continuation.  
**Purpose:** test whether the directionally positive but uncertain fresh geometry signal strengthens on genuinely future data, without adapting the model to the failed partial-August holdout.

## 1. Strict future boundary

The already-opened fresh source ends at:

`2026-08-20 23:58:00 UTC`

Primary continuation data must be strictly later than that source cutoff. Earlier data may be used only for causal detector warmup/state and may not enter future-confirmation outcomes.

No reaction outcome from the future-confirmation interval may be inspected before the mechanically frozen sample-size gate in section 5 is satisfied.

## 2. Frozen architecture and trigger

Retain unchanged:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

with:

- C5 refresh;
- sticky top-3;
- frozen arming/contact/consumption semantics;
- nearest causal upper-Z4 target;
- confirmed-M1-close-below-zlo invalidation;
- BUY only;
- US 08:00–17:00 America/New_York;
- `FIRST_BULL` = first confirmed M1 after contact satisfying only `close > open`;
- next available M1 open execution;
- no close-position threshold.

## 3. Frozen model — no adaptation after partial-August FAIL

Use exactly:

`XAUUSD_Z4_EBUY_FIRST_BULL_GEOMETRY_H1_FROZEN_MODEL_v1_0.json`

Blob:

`7064cd9c1ab91e76123b745be246ec1c57ef41cc`

Features, scaler, coefficients, intercept and H1 score cutpoints remain unchanged.

Frozen H1 geometry-score cutpoints:

- q20 = `0.2387694161370814`;
- q80 = `0.3273659155086846`.

No refit, calibration, coefficient update, feature selection, threshold search, session optimization or probability recalibration is allowed.

## 4. Source rule

Primary source remains the same Dukascopy XAUUSD M1 BID source family used in the historical and fresh studies.

Before opening future reaction outcomes:

- pin the exact source repository/commit or immutable acquisition manifest;
- record every raw file SHA-256;
- record first/last timestamps and row counts;
- verify timestamps are UTC milliseconds where applicable;
- verify the future primary interval begins strictly after `2026-08-20 23:58:00 UTC`.

A source-family change requires a separate pre-outcome provenance addendum and cannot silently replace the primary source.

## 5. Frozen sample-size gate

To avoid repeated outcome peeking, future-confirmation metrics may be opened only when the accumulated **future-only** sample satisfies both:

1. at least **25 complete market-active US sessions**;
2. at least **750 resolved FIRST_BULL observations**.

A complete market-active US session is a Monday-through-Friday New-York date with the complete required raw M1 path for 08:00–16:59 NY and at least one non-flat raw M1 (`high > low`) in the interval. This definition is frozen prospectively to avoid treating weekend flat/synthetic rows as trading sessions. It does not retroactively alter the already-decided partial-August test.

If either sample-size requirement is not met, status is:

`INSUFFICIENT_FUTURE_CONFIRMATION_SAMPLE`

and no AUC, score-band TP1 rate or other reaction-performance metric may be inspected or reported from that incomplete future sample.

## 6. Primary future-only confirmation gates

Once the sample-size gate is satisfied, bootstrap the complete eligible future US sessions with seed `20260827`, **2000 draws**.

`FUTURE_GEOMETRY_CONFIRMATION_PASS` requires all of:

1. frozen H1 six-feature model AUC > 0.50;
2. session-bootstrap 95% CI lower bound for AUC > 0.50;
3. TP1 positive rate for frozen geometry score >= q80 > rate for score <= q20;
4. session-bootstrap 95% CI lower bound for top-minus-bottom TP1-rate difference > 0.

The future-only sample is primary. The already-opened Aug-2-to-Aug-20 result is not pooled into these primary gates.

## 7. Secondary diagnostics

Report without affecting the primary decision:

- average precision;
- Brier score and constant-prevalence Brier;
- frozen close-position-only AUC and CI;
- six-feature minus close-position-only AUC and CI;
- legacy descriptive `close_pos >=0.70` subset N and TP1 rate;
- frozen q20/middle/q80 score-band N and TP1 rates;
- `range_v` univariate AUC;
- family/rank distributions;
- contact count, FIRST_BULL firing count and nonfire reasons;
- point-estimate comparison with the already-opened partial-August sample, clearly labeled non-independent historical context.

No secondary metric may rescue a failed primary gate.

## 8. Decision semantics

### PASS

Permits a new research/engineering cycle for a threshold-free `FIRST_BULL + continuous geometry` trigger. It still does not authorize reusing the legacy BR70-conditioned E_BUY_US model. A separate model/indicator integration and Pine parity gate remains required.

### FAIL

Stop the replacement line unless a materially new, preregistered hypothesis is developed from outcome-blind information. Retain BR70 only as the legacy trigger needed by its existing E-score lineage; do not claim 70% is a natural threshold.

### INSUFFICIENT

Accumulate more genuinely future data under this unchanged protocol. Do not inspect partial reaction outcomes.

## 9. Explicit prohibitions

Before the future sample is opened, do not:

- move 70% to 75/80/85/90%;
- refit the six-feature H1 model;
- tune q20/q80;
- add or remove candle features;
- change FIRST_BULL timing;
- change target/invalidation rules;
- select sessions using reaction outcomes;
- alter C5 cadence because of future reaction performance;
- modify Pine to promote the experimental geometry trigger.

The objective of this continuation is precision on a frozen hypothesis, not another optimization pass.
