# XAUUSD Reaction Zones — COMEX DEV_RANK1 Analysis Preregistration v1

Date: 2026-08-18
Status: frozen before DEV_RANK1 market-data acquisition.

## Purpose

DEV_RANK1 is a controlled feature-discovery block. It is not final strategy validation and it must not be used to promote a trading system directly.

Two scientific questions remain separate:

1. Existing XAUUSD POIs: does COMEX add incremental predictive information for reaction, rejection/acceptance and entry expectancy?
2. COMEX-native zones: do zones derived from the GC auction create predictive POIs independently of the existing XAUUSD zones?

No family is removed because of prior price-only performance.

## Data roles

Primary DEV_RANK1 analysis uses 96 analytical sessions across 2011–2018: 92 new sessions plus four already-paid pilot rank-1 sessions.

DEV_RANK2 is replication only. RETRO_CONFIRM and LOCKED_COMEX_TEST remain unopened during DEV_RANK1 development.

The two paid DEV rank-2 pilot sessions are not used until DEV_RANK2. Confirm/test pilot sessions remain QA-only and are replaced by the deterministic same-stratum rule.

## Independent unit and weighting

The independent cluster is `research_trading_date`, not an individual event.

Mandatory outputs:

- event-level estimates with standard errors / bootstrap clustered by trading date;
- session-level estimates giving each selected trading date one unit of influence before post-stratification;
- population-poststratified estimates using the frozen `year × quarter × vol_band` weights;
- family-specific estimates for DOZ_ONLY, OBJECTIVE_ONLY, MEMORY_ONLY, FVG_ONLY and CONFLUENCE.

A pooled screening model may be reported only with explicit family balancing so FVG cannot dominate merely because of event count. Population-weighted family results remain separate.

## Outcomes

### Existing-POI reaction outcome

Primary binary target: the existing preregistered `reaction_0_5sigma` label. Its definition is not changed during COMEX development.

### Auction-behavior outcome

Primary multiclass target: existing `behavior_v2` classes:

- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTED_BREAK
- UNRESOLVED

A binary rejection-versus-acceptance diagnostic may be derived only from a frozen mapping and cannot replace the multiclass primary result.

### Entry-model economic outcomes

For each frozen entry model:

- PASSIVE_TOUCH
- TOUCH_NEXT_OPEN
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTANCE_RETEST
- RECLAIM_PULLBACK

report trade eligibility, fill/retest probability and net-R expectancy separately. Do not combine non-filled setups with filled-trade expectancy.

Execution-cost scenarios remain those already frozen in the price-only research. No cost scenario may be selected because COMEX makes it look better.

## Baseline and nested feature groups

Every incremental COMEX comparison must use the same observations for baseline and augmented models.

### B0 — XAU baseline

Allowed baseline covariates already known before COMEX acquisition:

- broad family / exact constituent signature;
- side;
- session label;
- local hour;
- sigma60;
- zone_width_sigma;
- approach_direction;
- approach_band;
- constituent_count;
- frozen model identity where applicable.

No historical Phase-C winner flag or previously profitable-cell indicator is allowed.

### B1 — GC M1 context

Add only the frozen M1 feature dictionary.

### B2 — GC trades / auction

Add only the frozen trades feature dictionary, including native A/B/N treatment and profile features.

The primary incremental question is B2 versus B1 and B1 versus B0. Individual feature significance is secondary.

## Primary model classes

To limit researcher degrees of freedom:

- binary reaction: ridge logistic regression;
- multiclass behavior: ridge multinomial logistic regression;
- trade win/loss diagnostics: ridge logistic regression;
- net-R conditional on fill: ridge linear model plus nonparametric clustered bootstrap of mean-R differences.

All continuous predictors are winsorized only by training-fold quantiles if the feature dictionary explicitly permits it, then standardized using training-fold statistics only.

Ridge penalty grid is frozen to `C ∈ {0.01, 0.1, 1, 10, 100}`. Choice is made inside DEV_RANK1 only by leave-one-year-out cross-validated log loss for classification and squared error for R-regression.

Tree ensembles, neural networks and unconstrained feature search are exploratory only and cannot promote a feature group to DEV_RANK2.

## Validation inside DEV_RANK1

Use leave-one-year-out diagnostics across 2011–2018.

For every held-out year:

1. fit preprocessing and ridge hyperparameter on the other DEV_RANK1 years;
2. score the held-out year once;
3. store calibration and incremental metrics;
4. never use RETRO_CONFIRM or LOCKED_COMEX_TEST.

Report both pooled cross-fitted performance and the distribution across held-out years.

## Metrics

Reaction / binary targets:

- log loss (primary predictive metric);
- Brier score;
- calibration intercept/slope;
- ROC-AUC as secondary discrimination metric.

Multiclass behavior:

- multiclass log loss primary;
- macro Brier / one-vs-rest Brier;
- per-class calibration / recall as diagnostics.

Economic targets:

- mean net R conditional on fill;
- PF as descriptive only, not the primary inferential statistic;
- fill/retest probability;
- positive-year count;
- worst-year R;
- clustered confidence interval.

## Feature-group decision rule inside DEV_RANK1

A COMEX feature group is eligible to be frozen for DEV_RANK2 only if all are true:

1. cross-fitted metric improves the corresponding baseline in the expected direction;
2. improvement is not driven by a single year;
3. at least 5 of the 8 DEV years have non-adverse direction for the primary metric, unless a preregistered regime interaction explains the difference;
4. calibration does not materially deteriorate;
5. effect remains qualitatively present in both event-level and session-level analyses;
6. no forbidden post-decision information is used.

This is a discovery gate, not a p-value claim of final validation.

## Multiplicity

Feature *groups* are the unit of primary screening, not hundreds of individual transformations.

Within DEV_RANK1:

- Benjamini-Hochberg FDR 10% may be used for secondary individual-feature diagnostics within a predefined group;
- no individual feature enters DEV_RANK2 solely because its unadjusted p-value is small;
- the shortlist passed to DEV_RANK2 is frozen at the group/formula level.

RETRO_CONFIRM later uses a stricter 5% family-wise confirmation rule defined before that block is opened.

## Sparse cells

A cell is not declared negative merely because event count is small.

Every family × entry-model report must include:

- event count;
- independent trading-date count;
- year count;
- effective sample-size diagnostic under post-stratification weights.

Cells failing feasibility thresholds are labeled `INCONCLUSIVE` and are not merged opportunistically with other cells after outcomes are inspected.

## COMEX-native zone study

This study is separate from the existing-POI model.

Zones may be generated only from the frozen feature/zone specification. Primary candidates are completed prior-session and developing current-session auction levels available causally at the evaluation time.

Matched controls must preserve year, session/time-of-day, direction and volatility context. No zone is retained merely because its historical retests had positive R.

Future retests discovered from DEV_RANK1 zones are logged prospectively. If tick data at those future retests are not already available, only their timestamps are stored and their acquisition is deferred to a separately authorized Stage 2.

## Forbidden lookahead

- no COMEX record after the frozen decision cutoff for a model;
- no final current-session POC/VA/VWAP used before that session is complete;
- no profile built across a contract mapping change without an explicit reset;
- no using LOCKED_COMEX_TEST or RETRO_CONFIRM to select features, bin sizes, thresholds or model hyperparameters;
- no post-entry COMEX features for initial trade selection;
- no changing the XAU outcome labels because COMEX results are inconvenient.

## Freeze gate before DEV_RANK2

Before DEV_RANK2 can be opened, commit and hash:

1. raw-data/session QA report;
2. final feature dictionary and causal formulas;
3. exact COMEX-native zone rules;
4. feature-group shortlist;
5. ridge model / preprocessing procedure;
6. all weighting and clustering code;
7. DEV_RANK1 leave-one-year-out report;
8. list of every exploratory analysis that was run;
9. explicit statement that DEV_RANK2/CONFIRM/LOCKED_TEST remained unopened.

DEV_RANK2 is replication. It cannot be used as a second development set.
