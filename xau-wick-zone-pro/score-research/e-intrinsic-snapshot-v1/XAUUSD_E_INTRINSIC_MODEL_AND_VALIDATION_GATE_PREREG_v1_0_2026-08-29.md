# XAUUSD — E intrinsic model & validation gates preregistration V1

**Frozen date:** 2026-08-29  
**Scope:** BUY only, XAUUSD M1, US 08:00–17:00 New York  
**Prerequisites:** intrinsic ledger REAL QA PASS + Pro authorization to open DEV.

## 1. Scientific separation of periods

Historical dates are not relabeled as pristine OOS after prior project exploration.

### DEV_HISTORY

`2024-08-01T00:00:00Z <= contact_time < 2025-08-01T00:00:00Z`

Purpose: estimate the single frozen model only. This period is explicitly exploratory/developmental and cannot validate the score.

### HISTORICAL_REPLICATION_DIAGNOSTIC

`2025-08-01T00:00:00Z <= contact_time < 2026-08-01T00:00:00Z`

Purpose: locked historical replication diagnostic after model freeze. Because contamination history cannot be guaranteed to be zero, success here is supporting evidence, not final independent validation.

### PROSPECTIVE_CONFIRMATION

Starts with NY trading sessions on or after **2026-08-31**. No prospective result may be inspected until the predetermined information threshold is reached.

Primary prospective evaluation point: first completed checkpoint at which both are true:

- at least 1,000 primary eligible episodes;
- at least 90 completed NY trading sessions.

No interim performance peeking is permitted.

## 2. Frozen model family

If the Pro pre-outcome gate authorizes DEV opening, exactly one candidate model is fit:

- logistic regression;
- L2 penalty;
- `C = 1.0`;
- solver `lbfgs`;
- maximum iterations 5000;
- no class weighting;
- no hyperparameter search;
- no alternative algorithm competition.

## 3. Frozen V1 feature transformations

Model-row eligibility is frozen as `current_family != Z4 AND origin_family != Z4`. Z4-only provenance is structural context, not an intrinsic E feature.

Numeric:

- `zone_width_v`: DEV mean/standard deviation standardization;
- `episode_age_c5`: transform `log1p(age)` then DEV mean/standard deviation standardization.

Categorical:

- `current_family` and `origin_family` one-hot encoded;
- category vocabulary frozen from DEV in deterministic lexicographic order;
- first lexicographic category used as reference;
- unseen later categories map to all-zero categorical indicators and are reported.

No imputation is allowed for the four model features. Missing model features cause that episode to be excluded with an explicit reason and the missingness rate must be reported.

## 4. Frozen score mapping

After fitting on DEV only:

1. preserve the continuous model logit;
2. preserve the logistic predicted probability as a model output, but do not call it calibrated unless calibration is separately demonstrated;
3. create `E_REACTION_RANK_V1` as the empirical percentile of the continuous logit against the frozen DEV logit distribution.

The DEV CDF, coefficients, intercept, transforms, category vocabulary and quartile cutpoints are frozen before any later-period outcome is opened.

`E_REACTION_RANK_V1` is a rank, not an absolute probability and not a guaranteed force score.

## 5. Frozen quartiles

Q1/Q2/Q3/Q4 cutpoints are the 25th/50th/75th percentiles of the DEV score distribution. They are never recomputed on replication or prospective data.

## 6. Historical replication diagnostics

Report without retuning:

- continuous association between frozen score and primary binary outcome;
- success rate in fixed DEV quartiles;
- Q4-Q1 difference;
- bootstrap confidence intervals clustered by NY session date;
- score distribution drift;
- unseen-category rate and missingness.

Bootstrap: 5,000 cluster resamples by NY session date, fixed seed `20260829`.

Historical replication cannot authorize production by itself.

## 7. Prospective confirmation gate

At the single frozen prospective checkpoint, the candidate passes only if **all** conditions are met:

1. continuous score association with the primary binary outcome is positive and its 95% session-cluster bootstrap CI lower bound is > 0;
2. fixed-quartile primary success rates satisfy `Q1 <= Q2 <= Q3 <= Q4`;
3. `Q4 - Q1 > 0` and its 95% session-cluster bootstrap CI lower bound is > 0;
4. prospective data are split chronologically into three equal-count pre-specified sub-blocks after collection; `Q4-Q1` is positive in all three;
5. the result is not driven by severe missingness or an unseen-family regime: model-feature exclusion rate <= 2% and unseen-category rate <= 5%;
6. no coefficients, transforms, CDF, quartiles, outcome definitions or inclusion rules changed after DEV freeze.

Failure of any gate means `E_INTRINSIC_SCORE_NOT_VALIDATED_V1`.

## 8. Incremental Z4/context study

Only after intrinsic validation may a separate preregistered study compare:

- intrinsic E block only;
- `Z4_CONTEXT` only;
- entry-context block only;
- frozen combinations.

Z4 geometry is never retroactively inserted into the intrinsic score.

## 9. Production rule

No Pine production modification and no live trading filter may be based on V1 before prospective confirmation passes and a separate production-readiness review is completed.
