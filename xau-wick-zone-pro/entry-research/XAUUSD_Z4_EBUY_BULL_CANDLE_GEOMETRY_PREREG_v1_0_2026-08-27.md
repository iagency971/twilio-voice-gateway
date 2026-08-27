# XAUUSD Z4 / E-BUY — bullish reaction candle geometry preregistration v1.0

**Frozen:** 2026-08-27 before any new threshold-free bullish-candle geometry outcome is computed or inspected.  
**Scope:** US BUY only, 08:00–17:00 America/New_York.  
**Purpose:** test whether the current `BULL_REJECTION` concept has a defensible candle-geometry basis and whether the incumbent close-position threshold `>=0.70` is supported by a stable relationship rather than merely being an arbitrary prespecification.

## 1. Frozen location/contact engine

Use the already validated E-BUY architecture and contact definitions unchanged:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

- C5 refresh;
- sticky top-3;
- same arming/contact/consumption semantics as reaction DEV v1.0 plus its pre-outcome repairs;
- same frozen target: nearest causal upper-Z4 lower boundary from the latest confirmed C5 state at/before contact;
- same invalidation: first confirmed M1 close strictly below frozen contact-state `zlo`;
- all outcomes stop at 17:00 NY.

Existing contact tables are treated as immutable inputs:
- H1 contacts: `reaction-dev-h1-v1-0-precomputed-location/XAUUSD_Z4_EBUY_REACTION_DEV_H1_CONTACTS_v1_0.csv.gz`;
- H2 contacts: `ebuy-h2-validation-v1-0/XAUUSD_Z4_EBUY_H2_CONTACTS_v1_0.csv.gz`.

## 2. No 70% threshold in the new candidate definition

Define `FIRST_BULL` as the **first confirmed bullish M1 bar at or after the frozen first-contact bar** satisfying only:

`close > open`

There is **no close-position threshold**.

Search terminates without a candidate if, before that first bullish bar:
- the zone invalidates;
- the frozen TP1 target is already reached;
- the session reaches the last bar that cannot provide a next-M1 open before 17:00 NY.

If `FIRST_BULL` fires, analytical execution is the next available M1 open, as in the existing confirmation-trigger framework. If execution is at/above TP1, mark `TARGET_ALREADY_REACHED_BEFORE_TRIGGER` rather than a trade.

This preserves the current BULL_REJECTION timing framework except that the `close-position >=0.70` condition is removed.

## 3. Primary outcome

From next-M1 execution:
- `TP1_FIRST` = frozen upper-Z4 target reached before invalidation and US end;
- `INVALIDATION_FIRST` = first confirmed M1 close below frozen contact-state zlo before TP1;
- `NEITHER` = neither by US end;
- same-M1 unknowable ordering = `AMBIGUOUS`, excluded from resolved-rate denominators.

Binary model label for discrimination analyses:
- positive = `TP1_FIRST`;
- negative = `INVALIDATION_FIRST` or `NEITHER`;
- ambiguous excluded.

## 4. Candle geometry variables — continuous, fixed before outcomes

For FIRST_BULL bar with range `R = high-low > 0`:

1. `close_pos = (close-low)/R`.
2. `body_frac = (close-open)/R` (positive by definition).
3. `lower_wick_frac = (open-low)/R`.
4. `upper_wick_frac = (high-close)/R`.
5. `lower_wick_to_body = (open-low)/(close-open)`; use `log1p` only for modeling stability, retain raw value for reporting.
6. `range_v = R / v_contact`.
7. `low_penetration_zone_width = (zhi-low)/(zhi-zlo)`.
8. `close_vs_center_zone_width = (close-center)/(zhi-zlo)`.
9. `close_vs_zhi_zone_width = (close-zhi)/(zhi-zlo)`.
10. `body_zone_width = (close-open)/(zhi-zlo)`.

Known-at-trigger context recorded but not part of the primary candle-only model:
- TP1 distance from next-open in v;
- minutes to US end;
- slot rank;
- family;
- zone width/v;
- v_contact.

No future variable may enter any geometry feature.

## 5. Data roles

### H1 DEVELOPMENT
`2024-08-01 <= t < 2025-08-01 UTC`

H1 may be used to characterize shapes and derive any candidate change-point. H1 is development, not validation.

### H2 RETROSPECTIVE REPLICATION ONLY
`2025-08-01 <= t < 2026-08-01 UTC`

H2 reaction outcomes have already been opened for the incumbent BR/E-score research. Therefore H2 is **not pristine OOS for this new geometry study**. It may only test whether H1 relationships reproduce directionally under a fixed H1-derived specification. No new claim of independent OOS validation is permitted.

A future/fresh preregistered sample is required before replacing the production BR definition.

## 6. Primary analyses — no threshold fishing

### A. Marginal geometry maps
For each fixed continuous feature, report by H1 deciles:
- N;
- TP1 positive rate;
- 95% session-bootstrap CI.

Freeze H1 decile cutpoints and apply the exact cutpoints to H2. Do not recompute H2 quantiles.

### B. Continuous discrimination
For every geometry feature report:
- H1 univariate ROC AUC;
- H2 univariate ROC AUC with the same raw orientation;
- logistic slope fitted on H1 and evaluated without refitting on H2;
- H1 and H2 positive-rate difference between the H1 top and bottom quintile.

The incumbent `close_pos >=0.70` is reported as a **reference only**; it may not win merely because it is incumbent.

### C. Threshold-free candle model
Fit one H1 logistic model using only the 6 pure candle-shape features:
- close_pos;
- body_frac;
- lower_wick_frac;
- upper_wick_frac;
- log1p(lower_wick_to_body);
- range_v.

Use standardized H1 preprocessing and L2 logistic regression with fixed `C=1.0`; no hyperparameter search. Evaluate the frozen H1 model on H2 without refitting.

Report AUC, AP and Brier on H1 and H2.

### D. Natural change-point diagnostic for close_pos
On H1 only, compare:
1. a continuous linear logistic relation in `close_pos`;
2. a single binary change-point model `I(close_pos >= c)`.

Candidate `c` values are the sorted unique H1 close_pos values between the H1 20th and 80th percentiles. Select `c` maximizing H1 log-likelihood. Bootstrap whole US sessions (fixed seed 20260827, 1000 draws) and report the change-point distribution (median, 10th, 25th, 75th, 90th percentiles).

Apply the single H1-derived `c` to H2 **without movement** and report above/below N and positive rates with bootstrap CI.

Do not interpret a sharp threshold if:
- the threshold bootstrap distribution is broad/multimodal; or
- the continuous model is at least as good as the threshold model under session-blocked H1 cross-validation.

No arbitrary minimum effect-size threshold is introduced in this study. Report effect sizes and uncertainty directly.

## 7. Scientific interpretation categories

The result must be classified as one of:

1. `NO_GEOMETRY_SIGNAL` — candle geometry has weak/inconsistent discrimination and no stable monotonic/threshold pattern.
2. `CONTINUOUS_GEOMETRY_SIGNAL` — geometry is informative but no stable hard cutoff is supported; a continuous score is scientifically preferable.
3. `STABLE_CLOSEPOS_CHANGEPOINT_CANDIDATE` — H1 produces a concentrated change-point and the exact H1 cutoff reproduces direction/effect on H2; still requires fresh validation before replacing BR.
4. `MULTIVARIATE_REJECTION_GEOMETRY` — wick/body/range combination carries materially more reproducible information than close_pos alone; future trigger should be based on joint geometry rather than a single close-position threshold.

Multiple descriptive properties may coexist, but only one primary classification is emitted using the priority: multivariate > stable change-point > continuous > none when supported by the reported evidence.

## 8. Explicit nonclaims

This study does not by itself:
- validate a new production trigger;
- authorize changing Pine;
- validate live profitability or spread/slippage/commission;
- make H2 pristine again;
- claim that a visually named “rejection candle” has institutional/SMC authority.
