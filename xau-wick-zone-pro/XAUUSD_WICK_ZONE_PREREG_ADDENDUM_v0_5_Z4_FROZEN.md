# XAUUSD Wick-Zone Research — Addendum v0.5
## Z4 prospective freeze before VALIDATION

**Freeze date:** 2026-08-23  
**Status:** FROZEN BEFORE ANY VALIDATION/OOS READ  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Primary candidate:** `P_REVISIT_240` only  
**Reaction score:** NO-GO / not eligible for validation as a primary score

---

## 1. Purpose of this addendum

The original preregistration asked whether historical wick/body structure around price adds predictive information about future interaction. Early exact-level tests did not pass. Subsequent DEV-only work generated a more specific candidate: a *zone-level revisit probability* using outcome-blind mountain geometry plus causal zone lineage/stability features.

This document freezes that DEV-generated candidate **before opening any Validation or OOS data**. From this point forward, the primary validation architecture, features, coefficients, calibration map, metric definitions and pass/fail rules may not be altered in response to Validation outcomes.

No P&L is part of this gate.

---

## 2. Invalid legacy results remain excluded

The following earlier exploratory reports remain permanently invalid and cannot be used as evidence:

- `XAUUSD_DEV_PILOT_2024_07_M0_M2LITE_v0_1.md`
- `XAUUSD_DEV_M2_SPATIAL24H_DIRECTION_SESSION_REPORT_v0_1.md`

They contained figures presented before a true complete predictive run. Nothing in this freeze rehabilitates them.

---

## 3. Data source and DEV boundary

Source: public Dukascopy XAUUSD M1 dataset mirrored in `kevingtlin/Market-Data-Lab`.

DEV used only January through July 2024. Continuous BID and ASK runs were built independently.

Important verified BID SHA-256 values:

- 2024-01: `7414d1cf6a02cf4fff5347e79602e9109549622cb73b152e5462188cc797135d`
- 2024-02: `45060c59ccfc0ef3d5f78b49d793b7e3f97757a7659c604b887850068346621f`
- 2024-03: `28c82e54e1bd7f586f5d22c0c39d9217618f62e8dfdd7eab94602c2c2bb81a14`
- 2024-04: `ce55b0d9acdf20c694c37e3c53233455cc8b772269eb39f60357808abe37b9c9`
- 2024-05: `18084ecf8e9d5cef352cc290a55de29f27f006653b5da24a6520f8a02488f4f6`
- 2024-06: `f7cad6452e9666b37f6f7830bb69a61439095919bb1609daa80839fdb3a8fd39`
- 2024-07: `a1c432b64a36118f1934c9c838cee83c1f05181fbfd602452fd3d46acdd4fd52`

ASK was independently QA'd and hashed in `XAUUSD_Z4_DEV_SOURCE_MANIFEST_v0_1.json`.

Frozen evidence artifacts:

- `xau-wick-zone-pro/results/XAUUSD_Z4_DEV_SOURCE_MANIFEST_v0_1.json`
- `xau-wick-zone-pro/results/XAUUSD_Z4_CONTINUOUS_BID_summary.json`
- `xau-wick-zone-pro/results/XAUUSD_Z4_CONTINUOUS_ASK_summary.json`
- `xau-wick-zone-pro/results/XAUUSD_Z4_DEV_BID_ASK_COMPLETION_v0_1_results.json`
  - Git blob SHA: `fb90bb4ac1e05f7cafc2f0fc6abb278bd806513b`
- `xau-wick-zone-pro/results/XAUUSD_Z4_FROZEN_MODEL_PARAMS_v0_1.json`
  - Git blob SHA: `c95fd545ec451968cb421f81ed6add0c508f387d`

The frozen-parameter artifact explicitly states `FROZEN_DEV_MODEL_PARAMETERS_BEFORE_VALIDATION` and training through 2024-07-31 only.

---

## 4. Z4 zone construction — frozen

All operations are causal at landmark time.

### 4.1 Price field

- XAUUSD M1, each feed processed separately.
- Active M1: `high > low`; flat maintenance/inactive bars do not add interactions.
- Historical memory: last **1,440 active M1**.
- Price grid step: **0.01 USD**.
- Absolute grid origin: **0.00 USD**.
- Wick field is based on crossings of the lower/upper wick intervals, while body occupancy is retained separately as counter-information.

### 4.2 Volatility normalization and mountains

- Segmentation volatility `vseg`: median True Range over the same 1,440 active-M1 memory.
- Exact Gaussian smoothing in Python:
  - fine: `0.25 × vseg`
  - medium: `0.50 × vseg`
  - coarse: `1.00 × vseg`
- Coarse peaks define families/basins.
- Exactly one best medium peak is selected within each coarse family.
- A nearby fine peak is required as confirmation.
- Peak prominence is measured on the medium field.
- Zone bounds are the medium-peak width at **50% of prominence (P50)**.
- No `Top N` selection and no outcome-based threshold.

### 4.3 Z2/Z3/Z4 causal repairs

These were made outcome-blind to repair mechanics, not selected using future reaction results:

- **Z2:** fixed absolute 0.00 grid origin, eliminating dependence on a sample-global minimum.
- **Z3:** lineage age measured by exact active-bar index difference from zone birth, replacing a `15 × landmark-count` approximation.
- **Z4:** a missing eligible landmark terminates lineage; the matcher cannot silently bridge a gap where no eligible side-zone exists.

### 4.4 Lineage matching

Consecutive eligible 15-minute snapshots are matched one-to-one by a deterministic assignment cost combining:

- center distance normalized by `vseg`;
- interval overlap / IoU;
- relative width change.

A candidate match is eligible if center distance is within `1 × vseg` or the intervals overlap. No future outcome enters matching.

---

## 5. Outcome — frozen primary endpoint

For each zone snapshot at landmark `t`:

`REVISIT_240 = 1` if any of the next **240 active M1** overlaps the current zone interval `[zlo, zhi]`; otherwise 0.

The primary model is therefore a probability of *revisit*, not a probability of support/resistance reaction.

The horizon **240 active minutes** is primary because it existed before the final DEV gate. Other horizons observed in DEV may be reported only as secondary diagnostics and cannot replace H240 after seeing Validation.

---

## 6. Direction convention

- `side = -1`: zone below current close; BUY/support-side candidate, approached from above.
- `side = +1`: zone above current close; SELL/resistance-side candidate, approached from below.

BUY/SELL subgroup results are diagnostic only in the primary validation gate.

---

## 7. Session convention

Timezone: `America/New_York`, DST-aware.

- OVERNIGHT: 18:00–03:00
- LONDON_PRE_US: 03:00–08:00
- US: 08:00–17:00
- ROLLOVER: 17:00–18:00

US is diagnostically important for the intended manual use, but **US subgroup performance cannot rescue a failed global primary gate**.

---

## 8. Models — frozen

Both models use:

- `StandardScaler`, fit on DEV only;
- Logistic Regression;
- `C = 0.10`;
- solver `lbfgs`;
- `max_iter = 500`;
- `tol = 1e-6`;
- deterministic seed 44;
- sample weighting so every landmark has equal total weight regardless of how many zones it contains.

### 8.1 M0 — causal baseline

Features:

1. `side`
2. `dist_v`
3. `absdist_v`
4. `width_v`
5. `tr`
6. `trend15`
7. `trend60`
8. `trend240`
9. `week_sin`
10. `week_cos`
11. `landmark_us`
12. `log_exposure_center`

### 8.2 M0GL — candidate zone model

M0 plus frozen geometry/exposure and lineage/stability features:

Geometry/exposure:

- `log_prom`
- `log_bg`
- `log_strength`
- `log_mass`
- `log_peak`
- `same_share_center`
- `same_minus_body_center`
- `log_mean_wick`
- `log_mean_body`
- `wick_share_zone`
- `width_vseg`

Lineage/stability:

- `log_age_active`
- `log_age_civil`
- `center_shift_vseg`
- `width_log_change`
- `prom_log_change`
- `mass_log_change`
- `strength_log_change`
- `reinforce_streak`
- `center_sd4_vseg`
- `width_cv4`
- `prom_vs_histmax`

No feature may be added, removed, transformed differently or selected after opening Validation.

Exact scaler means/scales and coefficients/intercepts for BID and ASK are frozen in `XAUUSD_Z4_FROZEN_MODEL_PARAMS_v0_1.json`.

Primary Validation will use the **BID** frozen models. ASK may be run as a secondary feed-replication diagnostic and cannot rescue BID failure.

---

## 9. DEV evidence that justified opening Validation

This section is descriptive provenance, not a future pass criterion.

### 9.1 Continuous BID, chronological folds

Raw M0GL improvement over M0 for `REVISIT_240`:

| Fold | Δ Brier (M0 − M0GL) | Δ LogLoss (M0 − M0GL) |
|---|---:|---:|
| APR | +0.0012969675 | +0.0025115013 |
| MAY | +0.0015756988 | +0.0033401082 |
| JUN | +0.0018491785 | +0.0073547636 |
| JUL | +0.0012061727 | +0.0035159833 |

Pooled out-of-fold BID:

- Δ Brier: **+0.0014727645**
- Δ LogLoss: **+0.0040951363**

Weekly UTC robustness, 18 weeks:

- 14 / 18 weekly deltas positive;
- mean weekly Δ Brier: **+0.0014991956**;
- 10,000-week-bootstrap 95% interval: **[+0.0006910282 ; +0.0023455891]**.

### 9.2 Continuous ASK replication

Chronological raw Δ Brier:

- APR: +0.0007053636
- MAY: +0.0007955771
- JUN: +0.0027873332
- JUL: +0.0027844369

Pooled ASK:

- Δ Brier: **+0.0017428441**
- Δ LogLoss: **+0.0047776020**

Weekly UTC:

- 13 / 18 positive;
- mean weekly Δ Brier: +0.0019555802;
- 95% week-bootstrap: **[+0.0005757788 ; +0.0034426893]**.

Thus the DEV-only prospective gate for a revisit model passed on both BID and ASK. This is **not Validation**.

---

## 10. Reaction hypothesis remains NO-GO

DEV endpoints included:

- immediate/future positive direction at 5/15/30/60 min;
- MFE and adverse/far-side violation;
- sweep beyond far boundary;
- reclaim of far boundary;
- reclaim of peak;
- full reclaim;
- retest after reclaim.

The incremental zone/lineage information did **not** show sufficiently stable reaction performance across chronology, BUY/SELL and US subgroups. In particular, some reaction models deteriorated materially in later folds/subgroups.

Therefore:

- no `P_REACTION` model is promoted to Validation;
- no combined revisit×reaction score is allowed yet;
- the Pine `Strength 0–100` remains descriptive only.

---

## 11. Calibration — frozen but secondary to raw validation

A Platt calibration map was fit using DEV out-of-fold M0GL predictions.

Frozen BID calibration:

- intercept: **0.0608347660510048**
- slope: **1.1140415671004258**

Frozen ASK calibration:

- intercept: **0.06442704471645803**
- slope: **1.1179060385885173**

For a raw candidate probability `p_raw`:

`p_cal = sigmoid(platt_intercept + platt_slope × logit(p_raw))`

Calibration is for interpretation/user-facing probability only. It **cannot rescue** the primary raw M0GL-vs-M0 gate.

---

## 12. VALIDATION protocol — frozen prospectively

### 12.1 Period

Primary Validation period:

**2024-08-01 00:00 UTC through 2025-07-31 23:59 UTC**.

For causal warm-up/lineage state, earlier history may be processed, but only rows whose landmark is in the Validation interval are scored.

No data dated 2025-08-01 or later may be downloaded/read to complete Validation labels. Consequently, the final approximately 300 active M1 near the end of July 2025 may be conservatively unscored because the Z4 engine requires future-label headroom.

### 12.2 Primary feed

**BID**.

ASK is secondary feed robustness only.

### 12.3 Frozen predictions

Validation prediction must use the archived DEV scaler and logistic coefficients exactly. No fitting, recalibration, feature selection, threshold search or hyperparameter change is allowed on Validation.

### 12.4 Primary metrics

With equal total weight per landmark:

- `Brier(M0)`
- `Brier(M0GL)`
- `ΔBrier = Brier(M0) − Brier(M0GL)`
- `LogLoss(M0)`
- `LogLoss(M0GL)`
- `ΔLogLoss = LogLoss(M0) − LogLoss(M0GL)`

Primary uncertainty:

- group Validation rows by **UTC calendar week**;
- compute weekly ΔBrier;
- bootstrap weeks with replacement;
- seed 44;
- **10,000 resamples**;
- percentile 95% interval.

### 12.5 Prespecified halves

- VALIDATION-H1: 2024-08-01 through 2025-01-31
- VALIDATION-H2: 2025-02-01 through 2025-07-31

Each half is scored with the same frozen model.

### 12.6 PASS criteria

Primary BID Validation is `PASS` only if **all** are true:

1. global raw `ΔBrier > 0`;
2. lower bound of the 10,000-week-bootstrap 95% interval for ΔBrier is `> 0`;
3. global raw `ΔLogLoss >= 0`;
4. VALIDATION-H1 raw `ΔBrier >= 0`;
5. VALIDATION-H2 raw `ΔBrier >= 0`;
6. all causal/data-integrity QA gates pass.

If any item fails, status is `FAIL` or `INCONCLUSIVE` as appropriate, and OOS remains closed.

No BUY/SELL/US/ASK subgroup can rescue a failed primary BID gate.

---

## 13. Secondary Validation diagnostics — no model selection

If and only if computed without changing the frozen architecture, the following may be reported:

- BUY vs SELL;
- landmark session and first-touch session;
- US 08:00–17:00 ET;
- calibrated probability reliability/ECE;
- ASK replication;
- weekly sign count;
- distance/volatility strata.

They are descriptive robustness checks only. No subgroup discovery can redefine the primary claim after Validation is seen.

---

## 14. OOS remains sealed

OOS period is prospectively reserved as:

**2025-08-01 through 2026-07-31**.

It must not be accessed unless Validation passes the gate above.

If Validation passes, no model retraining on Validation is allowed for the primary OOS replication: OOS uses the same DEV-frozen M0, M0GL and Platt map. The exact OOS reporting/gate document will be committed before OOS is opened.

---

## 15. Interpretation allowed after Validation

Even a Validation PASS would establish only that the frozen zone/lineage variables improve prediction of **revisit within 240 active minutes** relative to the frozen causal M0 baseline.

It would **not** establish:

- profitable trading;
- support/resistance reaction probability;
- expected directional move;
- an entry rule;
- a stop/target rule;
- superiority of the current Pine Strength display.

A user-facing `P_REVISIT_240` score may only be promoted after Validation and final OOS replication satisfy their frozen gates.
