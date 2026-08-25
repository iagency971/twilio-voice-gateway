# XAUUSD Z4 — BULL_REJECTION + E_BUY_US H2 validation preregistration v1.0

**Frozen:** 2026-08-25 before any H2 reaction outcome is opened.  
**Scope:** BUY only, final historical holdout validation.

## 1. Frozen components

E-BUY location engine remains the OOS-replicated v0.4 sticky max-3 architecture.

Only the H1-selected trigger is permitted:
`BULL_REJECTION`.

No TOUCH_REF, RECLAIM_CENTER or RECLAIM_FULL H2 outcome may be computed in this validation.

Frozen score model:
- model: `M1_LOGISTIC` fallback freeze v1.1;
- model SHA-256: `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`;
- H1 training N = 7,110 resolved BULL_REJECTION entries;
- feature schema, preprocessing, coefficients and H1 training-score CDF are contained in the immutable model artifact and may not change.

`E_BUY_US` remains a percentile/rank, not a calibrated probability claim.

## 2. Holdout

H2 is opened only after this preregistration:
`2025-08-01 00:00 UTC <= t < 2026-08-01 00:00 UTC`.

Primary data: frozen Dukascopy XAUUSD BID monthly files. July 2025 may be used only as causal warmup for the first August 2025 Z4 geometry; no July outcome enters validation.

The already frozen OOS H2 E-BUY candidate table is used for displayed entry locations. Its coverage result already passed independently before reaction outcomes were opened.

## 3. Reaction definitions — unchanged

Use the reaction DEV v1.0 preregistration and Addenda A/B/C unchanged:
- one fresh contact per display episode/session;
- causal arming above zhi;
- first subsequent M1 overlap = contact;
- BULL_REJECTION = first post-contact confirmed bullish M1 with close-position >=0.70;
- execute at next available M1 open before 17:00 NY;
- no trigger if target was already reached before execution;
- invalidation = first confirmed M1 close below frozen contact-state zlo;
- TP1 = frozen nearest causal upper-Z4 lower boundary from the latest confirmed C5 state at/before contact;
- all outcomes stop at 17:00 America/New_York;
- same-M1 ordering uncertainty is ambiguous and excluded from resolved label fitting/evaluation.

No old REVISIT_240 endpoint defines H2 entry success.

## 4. Frozen E score features

Use exactly the v1.1 model artifact feature schema. Raw H2 M1 is used only to compute those causal trigger-time descriptors. No feature is added, removed, transformed or re-estimated outside the frozen preprocessing pipeline.

For every fired, non-ambiguous BULL_REJECTION H2 observation:
- raw M1 logistic score is produced by the frozen H1 pipeline;
- `E_BUY_US` = empirical percentile of that raw score in the frozen H1 training-score CDF.

Fixed bands:
- E>=80;
- E>=90.

No H2-derived recalibration or threshold movement is permitted.

## 5. H2 label

Positive = `TP1_FIRST`.

Negative = `INVALIDATION_FIRST` or `NEITHER` by 17:00 NY.

Ambiguous ordering is excluded from score metric denominators and reported separately.

## 6. Validation metrics

Report:
- fresh E-BUY contact count;
- BULL_REJECTION fired count/share;
- ambiguity share;
- unfiltered H2 positive rate;
- ROC AUC;
- average precision;
- Brier score and constant-baseline Brier;
- E>=80 count, positive rate and lift versus H2 baseline;
- E>=90 count, positive rate and lift versus H2 baseline;
- FP_1.00v_vs_0.50v favorable/adverse/ambiguous diagnostics overall, E>=80 and E>=90 (descriptive only);
- same metrics by H2 half-year (Aug 2025–Jan 2026 / Feb–Jul 2026) as stability diagnostics, not for retuning.

## 7. Frozen PASS gate

`E_BUY_US_H2_VALIDATION_PASS` requires all:

### Trigger viability
- fresh contact count >= 10,000;
- BULL_REJECTION fired count >= 3,000;
- fired share >= 25%;
- ambiguous TP/invalidation share <= 2%;
- unfiltered resolved H2 positive rate >= 20%.

### Score discrimination
- H2 ROC AUC >= 0.65;
- H2 AP >= H2 baseline positive rate + 0.10;
- frozen-model Brier < constant-baseline Brier.

### Operational score bands
- E>=80 N >= 800;
- E>=80 positive rate >= H2 baseline + 0.20 absolute;
- E>=80 positive rate >= 0.50;
- E>=90 N >= 350;
- E>=90 positive rate >= H2 baseline + 0.25 absolute;
- E>=90 positive rate >= 0.55;
- E>=90 positive rate >= E>=80 positive rate.

No failed check may be repaired by an H2-derived threshold, feature, family or time filter. A FAIL requires a new research cycle and H2 is considered spent for this specification.

## 8. Claims allowed on PASS

A PASS permits the historical claim that, on the frozen Dukascopy BID H2 holdout, the frozen E-BUY location engine + BULL_REJECTION + E_BUY_US rank generalized for selecting BUY entries targeting the frozen upper Z4 before invalidation/US close.

It still does **not** validate live profitability, CFD spread/slippage/commission, a hard SL, FOREXCOM entry-score transfer, `R_US`/route probability, or higher-timeframe R.
