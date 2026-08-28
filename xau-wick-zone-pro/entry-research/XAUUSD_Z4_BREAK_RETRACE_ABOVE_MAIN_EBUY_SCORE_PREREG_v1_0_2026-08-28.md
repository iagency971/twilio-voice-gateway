# XAUUSD Z4 breakout→retrace ABOVE_MAIN — E_BUY_US score study preregistration v1.0

**Frozen:** 2026-08-28 before opening the score/outcome interaction for this structural setup.

## 1. Question

Does the already frozen `E_BUY_US` rank add useful discrimination **inside the previously identified structural `ABOVE_MAIN` setup**?

This study does not create a new score and does not change the structural setup.

## 2. Frozen structural setup

US only: `08:00–17:00 America/New_York`.

Use the exact prior structural engine/output without modification:
- confirmed M1 close breaks a causal main Z4 upward;
- next higher causal Z4 is frozen at breakout as target;
- price must subsequently retrace at least by wick into the main Z4;
- E1/E2/E3 may be inside, overlap, above or below main Z4;
- wick below `main_zlo` is allowed;
- only confirmed M1 close strictly below `main_zlo` invalidates;
- after main-Z4 retrace, causal displayed E is touched and `BULL_REJECTION` fires (`close>open` and close-position >=0.70);
- execute next M1 open;
- TP = first touch of frozen next-higher-Z4 `target_zlo`;
- structural loss = first subsequent M1 close strictly below frozen main `main_zlo`;
- primary subgroup = `e_main_relation == ABOVE_MAIN` as defined by the prior frozen study (`E.zlo > main.zhi`).

Frozen structural engine blob: `7862638917015838948001a374f9bea7dba83e07`.
Historical structural evidence comes from workflow run `33139524456`, artifact `z4-break-retrace-e123-rejection-v1-1`.

No family, E rank, time-of-day, wick, RR, target, stop or geometry rule may be modified in this score study.

## 3. Frozen score

Use only the existing `E_BUY_US` v1.1 score:
- model: `M1_LOGISTIC`;
- frozen model SHA-256: `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`;
- trained on 7,110 resolved H1 official E-BUY BULL_REJECTION observations;
- `E_BUY_US = 100 * empirical percentile in the frozen H1 training-score CDF`;
- E is a rank, **not a calibrated probability**.

No refit, recalibration, new feature, coefficient, CDF or score definition is allowed.

## 4. Score provenance by window

### H1

For H1, use only the official OOF `M1_LOGISTIC` scores produced before the frozen full-H1 fit:
`ebuy-score-dev-v1-0/XAUUSD_Z4_EBUY_SCORE_DEV_OOF_v1_0.csv.gz`.

The OOF folds cover only `2024-12-01 <= observation_time < 2025-08-01`.
Therefore H1 structural trades from Aug–Nov 2024 legitimately have no OOF score and must be reported as unavailable, not scored in-sample.

Map OOF rows to the official H1 BULL_REJECTION trigger table through the original official E-BUY episode identity, then map to structural trades by exact causal event identity:
- same `trigger_time`;
- same `family`;
- same E slot/rank (`slot_rank == structural entry_rank`);
- same E geometry (`zlo`, `center`, `zhi`) within numerical tolerance.

### H2

Use the already frozen-model H2 scored table:
`ebuy-h2-validation-v1-0/XAUUSD_Z4_EBUY_H2_SCORED_v1_0.csv.gz`.

Map to structural trades with the same exact event identity fields above.

## 5. Mapping gate

Before interpreting score performance, report for `ABOVE_MAIN` in each window:
- structural executed count;
- structural terminal count;
- score-matched terminal count;
- score coverage share;
- zero-match count;
- multi-match/ambiguous count.

Any structural trade with no unique official score match remains unscored and is excluded from score-performance metrics.
No synthetic score may be imputed.

## 6. Primary outcome

Primary terminal label:
- positive = structural `TP_FIRST`;
- negative = structural `INVALIDATION_FIRST`.

`NEITHER` and `AMBIGUOUS` are reported but excluded from primary terminal AUC/win-rate denominators.

The score is evaluated against the **new structural target/invalidation**, not against the old score-training TP1 label.

## 7. Primary score analysis

For H1 OOF and H2 separately, on uniquely score-matched terminal `ABOVE_MAIN` trades:
- N, TP, invalidation, unfiltered terminal TP rate;
- ROC AUC using continuous `E_BUY_US`;
- session-cluster bootstrap 95% CI for AUC, seed `20260828`, 10,000 replicates; invalid one-class replicates dropped and count reported;
- Spearman rank correlation between E and binary structural outcome, descriptive;
- median E for TP and invalidation.

This continuous analysis is primary. No cutoff is selected from these data.

## 8. Fixed threshold table — descriptive secondary analysis

Report the following cumulative bands exactly:
- all scored (`E>=0`);
- `E>=50`;
- `E>=60`;
- `E>=70`;
- `E>=80`;
- `E>=90`.

For every threshold and window report:
- terminal N;
- TP / invalidation counts;
- terminal TP rate;
- Wilson 95% CI;
- absolute lift versus the same-window all-scored `ABOVE_MAIN` baseline;
- structural expectancy in R before costs (TP contributes its frozen `nominal_rr`, invalidation contributes `-1R`);
- theoretical PF_R = sum winning nominal R / loss count.

Also report exclusive E deciles/bands only as descriptive diagnostics if sample size permits; they must not be used to select a cutoff.

## 9. Stability interpretation

Because `ABOVE_MAIN` was discovered after viewing the historical structural H1/H2 output, neither H1 nor H2 can independently promote a production rule for this subgroup.

Allowed interpretation:
- whether frozen E rank is directionally associated with better structural outcomes;
- whether the relationship is stable in sign across H1 OOF and H2;
- whether existing operational bands E80/E90 enrich the structural candidate.

Forbidden interpretation:
- selecting a new optimal E threshold from 50/60/70/80/90;
- claiming live profitability;
- claiming calibrated probability;
- production promotion from this retrospective interaction alone.

## 10. Evidence classification

After results are opened, classify only as:

- `E_SCORE_DIRECTIONALLY_SUPPORTED` if continuous AUC point estimate is >0.50 in **both** H1 OOF and H2 and the H2 session-bootstrap AUC lower 95% bound is >0.50;
- `E_SCORE_DIRECTIONAL_BUT_UNCERTAIN` if both AUC point estimates are >0.50 but the H2 lower bound is <=0.50;
- `E_SCORE_NOT_STABLE` if the AUC direction is <=0.50 in either window;
- `E_SCORE_MAPPING_INSUFFICIENT` if H2 has fewer than 20 uniquely score-matched terminal `ABOVE_MAIN` trades or mapping ambiguity exceeds 2% of matched+ambiguous candidates.

`E_SCORE_MAPPING_INSUFFICIENT` takes precedence over the discrimination labels.

No threshold-specific promotion is authorized by any classification.
