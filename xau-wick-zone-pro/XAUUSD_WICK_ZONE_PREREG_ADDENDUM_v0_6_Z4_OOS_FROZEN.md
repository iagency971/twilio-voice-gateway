# XAUUSD Wick-Zone Research — Addendum v0.6
## Z4 OOS prospective freeze after VALIDATION PASS

**Freeze date:** 2026-08-23  
**Status:** FROZEN BEFORE ANY OOS DATA READ  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Primary candidate:** `P_REVISIT_240`  
**Primary feed:** BID  
**Reaction score:** still NO-GO

---

## 1. Preconditions

The DEV-generated Z4 revisit candidate was frozen in:

- `XAUUSD_WICK_ZONE_PREREG_ADDENDUM_v0_5_Z4_FROZEN.md`
- prereg commit: `281070c91f9fc8a504cb6d08f84e11ed765e1d0c`

Validation was then opened and scored with the original DEV-frozen parameters, with no fitting on Validation.

Frozen Validation result:

- `xau-wick-zone-pro/validation/XAUUSD_Z4_VALIDATION_RESULTS_v0_1.json`
- Git blob SHA: `d7a5120e58c9fa39c78d0453c417cd0694522e05`
- status: `PASS`

### Validation primary BID evidence

- scored zone rows: **134,272**
- landmarks: **23,518**
- raw Brier M0: **0.1394336344**
- raw Brier M0GL: **0.1372729365**
- raw ΔBrier M0−M0GL: **+0.0021606979**
- raw ΔLogLoss M0−M0GL: **+0.0064640617**
- UTC weeks: **53**
- positive weekly ΔBrier: **41 / 53**
- weekly mean ΔBrier: **+0.0021757204**
- 10,000-week-bootstrap 95% interval: **[+0.0013474159 ; +0.0030235919]**
- Validation H1 ΔBrier: **+0.0019276763**
- Validation H2 ΔBrier: **+0.0023973542**

All six prospectively frozen Validation checks passed.

Validation secondary ASK also had positive global skill:

- ΔBrier: **+0.0019110452**
- ΔLogLoss: **+0.0058680612**
- weekly 95% interval: **[+0.0010987596 ; +0.0027879988]**

ASK remains secondary and cannot determine the primary OOS gate.

---

## 2. What remains frozen from DEV

No model parameter is changed after Validation.

The exact DEV parameter artifact remains:

- `xau-wick-zone-pro/results/XAUUSD_Z4_FROZEN_MODEL_PARAMS_v0_1.json`
- Git blob SHA: `c95fd545ec451968cb421f81ed6add0c508f387d`

The exact Z4 causal engine remains:

- `xau-wick-zone-pro/xau_zone_episode_dev_z4.py`
- Git blob SHA: `a8a147615c3fd366c49e93b340fd2018b5b66e9e`

The primary raw models remain M0 vs M0GL with:

- same feature lists;
- same transforms;
- same DEV scaler means/scales;
- same DEV logistic coefficients/intercepts;
- `C=0.10`, `lbfgs`, `max_iter=500`, `tol=1e-6`;
- equal total weight per landmark.

The DEV Platt map also remains unchanged and is diagnostic/user-facing only. It cannot rescue the raw OOS gate.

---

## 3. OOS period — frozen

Primary OOS interval:

**2025-08-01 00:00 UTC through 2026-07-31 23:59 UTC**.

For causal warm-up and lineage state, the Z4 engine may process earlier historical rows back to January 2024. This is permitted because those rows precede each OOS landmark.

No data dated **2026-08-01 or later** may be downloaded/read for the OOS run. The final approximately 300 active M1 of July 2026 may therefore be conservatively unscored because future-label headroom is unavailable without crossing the reserved boundary.

---

## 4. OOS primary endpoint — unchanged

`REVISIT_240 = 1` if any of the next 240 active M1 overlaps the current frozen zone interval `[zlo, zhi]`; otherwise 0.

This is a revisit model, not a reaction model.

No alternative horizon may replace 240 after seeing OOS.

---

## 5. OOS scoring code — frozen before OOS

- `xau-wick-zone-pro/xau_wick_zone_oos_score.py`
- Git blob SHA: `b9702145ec53849482dd0374af52fa506d4491b3`

This script:

- loads the original DEV-frozen M0 and M0GL parameters;
- performs no fitting/retraining;
- scores only OOS landmarks;
- computes the same equal-landmark-weighted Brier and LogLoss metrics;
- groups uncertainty by UTC calendar week;
- bootstraps 10,000 weeks with seed 44;
- reports prespecified OOS halves and diagnostic BUY/SELL/US groups.

---

## 6. OOS halves — frozen

- **OOS-H1:** 2025-08-01 through 2026-01-31
- **OOS-H2:** 2026-02-01 through 2026-07-31

---

## 7. OOS PASS gate — frozen

Primary BID OOS is `PASS` only if **all six** conditions hold:

1. global raw `ΔBrier = Brier(M0) − Brier(M0GL) > 0`;
2. lower bound of the UTC-week 10,000-bootstrap 95% interval for ΔBrier is `> 0`;
3. global raw `ΔLogLoss >= 0`;
4. OOS-H1 raw `ΔBrier >= 0`;
5. OOS-H2 raw `ΔBrier >= 0`;
6. all source/code/causal/data-integrity QA gates pass.

If any criterion fails, `P_REVISIT_240` is not promoted as an independently replicated predictive score.

ASK, BUY/SELL, US and calibration diagnostics cannot rescue a primary BID failure.

---

## 8. Calibration diagnostic repair

The primary Validation gate is unaffected, but a secondary diagnostic issue was discovered after Validation PASS:

`calibrated_m0gl_diagnostic.ece10` in Validation v0.1 recomputed equal-landmark weights *inside each probability bin*. The within-bin mean prediction/observed values are interpretable, but the reported bin `weighted_mass` and ECE aggregation are not the intended globally weighted ECE.

This bug did **not** affect:

- raw M0 or M0GL predictions;
- Brier;
- LogLoss;
- weekly bootstrap;
- half-period results;
- the Validation PASS decision;
- the frozen Platt coefficients.

For OOS, ECE is calculated correctly using the original global equal-landmark row weights before binning. This calibration diagnostic remains secondary and cannot affect PASS/FAIL.

The frozen BID Platt map remains:

- intercept `0.0608347660510048`
- slope `1.1140415671004258`

No recalibration on Validation is allowed before OOS.

---

## 9. Interpretation if OOS passes

An OOS PASS will support the narrow claim that the frozen Z4 geometry + lineage/stability information adds reproducible predictive information for **revisit within 240 active minutes**, above the frozen causal M0 baseline.

It will still not establish:

- reaction/rejection probability;
- profitability;
- entry/SL/TP logic;
- a BUY/SELL trade recommendation;
- that the Pine descriptive Strength is a probability.

Only after OOS can we decide how to expose the validated revisit information as a user-facing score, and whether calibration is good enough to call that score a probability rather than a relative predictive index.

---

## 10. Reaction branch remains closed

The sweep/reclaim/retest and directional endpoints remain scientifically interesting but did not achieve the stability required in DEV. They are not permitted to piggyback on a successful revisit result.

A future reaction score would require its own new development and independent holdout plan.
