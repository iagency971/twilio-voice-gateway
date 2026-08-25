# XAUUSD Z4 — E_BUY_US score development preregistration v1.0

**Frozen:** 2026-08-25 after the preregistered H1 reaction DEV selected `BULL_REJECTION`, before any H2 reaction outcome is opened and before any E_BUY_US model result is computed.  
**Scope:** BUY only. H1 development only. H2 reaction holdout remains closed.

## 1. Frozen upstream state

Location engine is frozen and OOS-replicated:
`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`, sticky max-3 display.

Reaction trigger is frozen from the preregistered H1 selection rule:
`BULL_REJECTION`.

Known aggregate H1 result at freeze: 16,896 fresh contacts, BULL_REJECTION fired 7,128 (42.1875%); it was DEV_ELIGIBLE and selected by the pre-existing lexicographic rule. This aggregate result is allowed development information. No H2 reaction result has been computed or inspected.

## 2. Score meaning

`E_BUY_US` is **not** Z4 `R` and is not a calibrated probability claim.

It is a 0–100 empirical percentile/rank of model score, intended to answer:

> after a causal BULL_REJECTION entry signal on a displayed E-BUY zone, how favorable is the known-at-entry configuration for reaching the frozen upper Z4 TP1 before zone invalidation and before 17:00 New York?

Primary label among fired BULL_REJECTION episodes:
- positive = `TP1_FIRST`;
- negative = `INVALIDATION_FIRST` or `NEITHER` by 17:00 NY;
- `AMBIGUOUS` observations are excluded from model fitting/evaluation and counted separately.

## 3. Frozen H1-only data

REACTION_DEV only:
`2024-08-01 00:00 UTC <= t < 2025-08-01 00:00 UTC`.

Primary source: frozen Dukascopy XAUUSD BID monthly files, hashes from the historical source manifest.

The already published H1 BULL_REJECTION trigger table from reaction DEV v1.0 is the outcome source. Raw H1 M1 may be used only to add the fixed causal trigger-bar descriptors below.

No raw H2 file may be downloaded by the score-development workflow.

## 4. Fixed known-at-entry features

No Z4 REVISIT_240 outcome or future feature is allowed.

Continuous/numeric:
- `slot_rank`
- `episode_age_c5`
- `zone_width_v`
- `arm_center_distance_v`
- `tp_distance_v`
- `minutes_to_us_end`
- `v_contact`
- `trend5_v`, `trend15_v`, `trend60_v`, `trend240_v`
- `contact_penetration_width`
- `contact_bull`
- `contact_close_position`
- causal `upper_z4_count` from the frozen H1 C5 candidate table
- `minutes_contact_to_trigger`
- BULL_REJECTION trigger candle `body_v`
- trigger candle `range_v`
- trigger lower wick / v
- trigger upper wick / v
- trigger close-position in candle
- trigger close minus contact-state `zhi`, in v
- trigger close minus contact-state center, in v
- next-open execution gap from trigger close, in v
- maximum penetration from contact through trigger, `(zhi - minimum low)/zone_width`.

Categorical:
- current `family`
- `episode_origin_family`
- frozen US subperiod (`US_EARLY`, `US_MORNING`, `US_AFTERNOON`).

`approach5_v` and `approach15_v` are excluded because the current reaction table duplicates the frozen trend5/trend15 diagnostics.

No feature selection based on univariate outcome inspection is allowed before the model comparison below.

## 5. Fixed temporal walk-forward folds

Four expanding-window folds:
1. train Aug–Nov 2024; test Dec 2024–Jan 2025;
2. train Aug 2024–Jan 2025; test Feb–Mar 2025;
3. train Aug 2024–Mar 2025; test Apr–May 2025;
4. train Aug 2024–May 2025; test Jun–Jul 2025.

Only resolved/non-ambiguous BULL_REJECTION observations are used for model fitting.

## 6. Fixed candidate models

### M1 — regularized logistic
- median imputation fitted on train only;
- standard scaling numeric train only;
- one-hot categorical with unknown-category ignore;
- logistic regression L2, `C=1.0`, `max_iter=2000`, deterministic solver `lbfgs`.

### M2 — histogram gradient boosting
- same train-only median imputation;
- one-hot categorical encoded dense;
- `HistGradientBoostingClassifier` with fixed parameters:
  - learning_rate = 0.05
  - max_iter = 200
  - max_depth = 3
  - min_samples_leaf = 50
  - l2_regularization = 1.0
  - random_state = 20260825.

No hyperparameter search is authorized in v1.0.

## 7. E percentile mapping

For each fold/model:
- fit only on the fold training period;
- obtain train and test raw positive scores;
- map each test score to `E_BUY_US` by its empirical percentile in the **training-score distribution only**.

Thus fixed operational bands are available without peeking at the test distribution:
- `E >= 80` = selective candidate;
- `E >= 90` = high-confidence candidate.

## 8. Model selection and DEV gate

Report per fold and pooled OOF:
- ROC AUC;
- average precision (AP);
- Brier score;
- baseline positive rate;
- E>=80 count and positive rate;
- E>=90 count and positive rate;
- BULL_REJECTION `FP_1.00v_vs_0.50v` favorable/adverse/ambiguous diagnostics by E band, descriptive only.

Select between M1 and M2 by:
1. highest mean fold AP;
2. highest pooled OOF ROC AUC;
3. lowest pooled Brier;
4. deterministic preference M1 then M2.

`E_BUY_US_DEV_PASS` requires for the selected model, on pooled OOF:
- ROC AUC >= 0.60;
- AP >= pooled OOF baseline positive rate + 0.05;
- E>=80 has >=800 observations and positive rate >= baseline + 0.08 absolute;
- E>=90 has >=350 observations and positive rate >= baseline + 0.12 absolute;
- at least 3 of 4 folds have E>=80 positive rate strictly above that fold baseline.

If the gate fails, H2 stays closed and no production E score is claimed.

If it passes:
- refit the selected model with identical preprocessing/parameters on all resolved H1 BULL_REJECTION observations;
- freeze model parameters, preprocessing schema, feature order, H1 training-score CDF and SHA-256 artifacts;
- create a **new H2 validation preregistration before any H2 reaction outcome is opened**.

## 9. Explicit nonclaims

This DEV study does not validate:
- H2 performance;
- live profitability, spread, slippage or commissions;
- a hard SL;
- an `R_US` or route score;
- higher-timeframe R;
- calibrated probability interpretation of E_BUY_US.
