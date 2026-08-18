# XAUUSD / COMEX — DEV_RANK1 entry fill / availability model freeze v1

Date: 2026-08-18
Status: frozen before reading model-specific decision-feature manifests or COMEX-conditioned fill results.

## Scope

Six entry models remain separate:
- PASSIVE_TOUCH
- TOUCH_NEXT_OPEN
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTANCE_RETEST
- RECLAIM_PULLBACK

Decision populations and causal cutoffs are controlled by `COMEX_DEV_RANK1_ENTRY_DECISION_POPULATIONS_FREEZE_v1.md`.

## Sample for each B0/B1/B2 comparison

For a given entry model, fit/evaluate B0, B1 and B2 on exactly the same decision rows for which `b2_available == True` at that model's frozen `decision_time`.

Rows with missing/outside-GC B2 are reported in availability counts but are not silently imputed into the primary incremental comparison. This mirrors the frozen primary reaction/behavior comparison design.

## Outcome

Binary `fill_or_entry` from the already-frozen XAU execution model:
- PASSIVE_TOUCH: standing center-limit fill within frozen wait window;
- TOUCH_NEXT_OPEN: executable next-open entry availability;
- CLEAN_REJECTION: executable rejection entry after confirmed reclaim;
- FAILED_AUCTION: executable entry after confirmed failed-auction reclaim;
- ACCEPTANCE_RETEST: retest-limit fill after accepted break;
- RECLAIM_PULLBACK: pullback-limit fill after confirmed reclaim.

No COMEX feature may alter the historical XAU entry rule, wait window, fill price, stop, target or transaction cost.

## Model class

Primary: ridge logistic regression, identical preprocessing philosophy to the preregistered reaction model.

- C grid: `{0.01, 0.1, 1, 10, 100}`
- outer validation: leave-one-year-out, 2011–2018
- C selection: inner leave-one-year-out on the remaining years
- categorical imputation/OHE learned on training only
- numeric median imputation + missing indicators + standardization learned on training only
- seed 971

## Feature groups

- B0 = frozen XAU baseline features
- B1 = B0 + frozen continuous GC M1 context
- B2 = B1 + frozen causal raw-trades / auction features at the entry-model decision cutoff

Same frozen exclusion of pure QA identifiers/timestamps as the primary reaction/behavior models.

## Weighting / inference

Primary: family-balanced event weighting.
Sensitivities:
- population post-stratified event weighting;
- session-balanced weighting.

Trading date is the independent bootstrap cluster.

For every model report:
- decision population count;
- B2-available count;
- filled/entered and non-filled counts;
- fill/entry rate;
- session count;
- year count;
- family counts;
- annual outcome counts.

## Identifiability rule

No arbitrary optimization threshold is introduced.

Nested fitting is scientifically interpretable only if the training folds contain both outcome classes. If a required training fold is single-class, that entry model is `NON_IDENTIFIABLE` for the frozen nested procedure and receives descriptive counts only.

A test year with a single outcome class may still contribute log-loss/Brier but not a meaningful year-specific AUC; AUC is reported missing for that fold.

Sparse minority outcomes / few independent sessions are explicitly marked `UNDERPOWERED` or `INCONCLUSIVE`; they are never converted into a negative conclusion merely because a directional gate fails.

## Metrics

Primary scoring: cross-fitted log-loss.
Secondary:
- Brier score;
- ROC AUC where identifiable;
- calibration diagnostics where identifiable.

Incremental comparisons:
- B1 vs B0
- B2 vs B1

For each comparison report:
- family-balanced improvement;
- population-event improvement;
- session-balanced improvement;
- year-by-year improvements;
- count of positive/non-adverse years;
- trading-date cluster bootstrap 95% interval.

## Directional gate

The existing DEV_RANK1 directional gate is retained for consistency:
- family-balanced cross-fitted log-loss improvement > 0;
- session-balanced direction > 0;
- at least 5/8 outer years positive/non-adverse under the frozen annual calculation.

Bootstrap confidence is reported separately and is required for any claim of robust improvement; a directional-gate pass with a bootstrap interval spanning zero is not a strong promotion signal.

## Prohibitions

After seeing results, do not:
- tune a probability threshold;
- drop years;
- remove FVG to improve aggregate scores;
- promote a rare family/model cell as the new primary target;
- change the entry population;
- change decision times;
- change C grid/model class merely to rescue a failed result.

Net-R conditional on fill is a separate later target. No RR is selected in this fill analysis.
