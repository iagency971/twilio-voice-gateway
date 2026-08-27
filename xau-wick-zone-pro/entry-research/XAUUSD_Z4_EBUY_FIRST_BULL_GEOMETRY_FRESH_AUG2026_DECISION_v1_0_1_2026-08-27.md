# XAUUSD Z4 / E-BUY — FIRST_BULL geometry fresh US Aug-2026 decision v1.0.1

**Decision date:** 2026-08-27  
**Scope:** BUY only, US 08:00–17:00 America/New_York, C5.  
**Primary status:** `FRESH_GEOMETRY_SIGNAL_FAIL`  
**Pine authorization:** `NONE`

## 1. Frozen scientific lineage

The fresh test was preregistered before any August-2026 US `FIRST_BULL` reaction outcome was opened:

`xau-wick-zone-pro/entry-research/XAUUSD_Z4_EBUY_FIRST_BULL_GEOMETRY_FRESH_AUG2026_PREREG_v1_0_2026-08-27.md`

Frozen prereg blob:

`3b979eb3851bf65d87e3bf44cb24bd9eb9a5d640`

The candidate model was frozen separately before fresh outcomes:

`xau-wick-zone-pro/entry-research/XAUUSD_Z4_EBUY_FIRST_BULL_GEOMETRY_H1_FROZEN_MODEL_v1_0.json`

Frozen model blob:

`7064cd9c1ab91e76123b745be246ec1c57ef41cc`

No model refit, feature modification, score calibration, close-position threshold optimization or H1 q20/q80 movement occurred on the fresh sample.

## 2. Fresh source provenance

Source repository:

`kevingtlin/Market-Data-Lab`

Pinned source commit:

`91e3942741d670687e929d9842fc71c0af16f4ec`

August BID M1 file:

`xauusd_bid_m1_2026_08.csv`

Raw SHA-256 frozen before the original fresh outcomes:

`4f61d531018a8e8c37b1f410945e1d23d59fee96cde13bef223dcc9e63d0f852`

Rows: **24,115**.  
Available source interval: **2026-08-02 00:00 UTC through 2026-08-20 23:58 UTC**. The August file is therefore a partial-month fresh holdout, not a complete August sample.

July 2026 was used only for causal state/warmup leading into August, per preregistration.

## 3. Corrected immutable run

Corrected workflow run:

`33127229766`

Workflow head:

`b59302a83d3024c9bb2146f2dc07f7a9eeabd0e9`

Artifact:

`first-bull-geometry-fresh-aug2026-us-v1-0-1`

Artifact ID:

`9668888555`

Artifact digest:

`sha256:aefb64a82356bba8da7bc5bfd2663e4ededcf0f54e40bab4f233e3650d55c87b`

Corrected result JSON SHA-256:

`f2ff5e6392014097f2e0125a5638764fb42fe5d144c3730a8b23bb6a3cd5c5bc`

## 4. Mandatory engineering correction

During QA of the first fresh artifact, a bootstrap implementation mismatch was found: the AUC helper derived its resampling universe from non-empty resolved-event sessions, while the preregistration required whole mechanically eligible US sessions. Three eligible raw sessions had zero resolved `FIRST_BULL` events.

Before the corrected rerun, the correction was explicitly recorded in:

`XAUUSD_Z4_EBUY_FIRST_BULL_GEOMETRY_FRESH_AUG2026_PREREG_ADDENDUM_A_BOOTSTRAP_CLUSTER_UNIVERSE_2026-08-27.md`

The corrected run resamples all **17 mechanically eligible raw US sessions**, including zero-event clusters. No observation, outcome, score, model coefficient, scaler value, feature, H1 cutpoint, source byte stream, point estimate or decision rule was changed.

This is a deterministic prereg-compliance correction of the already-opened holdout, not a second fresh validation.

## 5. Sample adequacy

Mechanically eligible raw US sessions: **17**.  
Contacts: **973**.  
`FIRST_BULL` events: **480**.  
Resolved `FIRST_BULL` observations: **480**.

Outcome counts:

- `TP1_FIRST`: **157**;
- `INVALIDATION_FIRST`: **308**;
- `NEITHER`: **15**.

Overall TP1-positive rate: **32.7083%**.

Preregistered adequacy gate:

- >=8 eligible sessions: **PASS**;
- >=300 resolved FIRST_BULL observations: **PASS**.

The sample is therefore `ADEQUATE` under the frozen preregistration.

## 6. Primary confirmatory results

### Frozen H1 six-feature geometry model

AUC: **0.5381376822**.  
Whole-session bootstrap 95% CI: **[0.4858684052, 0.5834577037]**.

Primary AUC gates:

- point AUC > 0.50: **PASS**;
- bootstrap 95% CI lower bound > 0.50: **FAIL**.

### Frozen H1 geometry-score bands

Frozen H1 score cutpoints:

- q20: `0.2387694161370814`;
- q80: `0.3273659155086846`.

Fresh results:

| Frozen score band | N | TP1 positive rate |
|---|---:|---:|
| <= q20 | 97 | 28.8660% |
| middle | 299 | 33.1104% |
| >= q80 | 84 | 35.7143% |

Top-minus-bottom difference: **+6.8483 percentage points**.  
Whole-session bootstrap 95% CI: **[-8.0753 pp, +19.6527 pp]**.

Primary band gates:

- top rate > bottom rate: **PASS**;
- bootstrap 95% CI lower bound > 0: **FAIL**.

Because both uncertainty gates were preregistered as mandatory, the overall primary classification is:

`FRESH_GEOMETRY_SIGNAL_FAIL`

## 7. Secondary diagnostics

Frozen six-feature model:

- average precision: **0.3676129066**;
- Brier score: **0.2225220584**;
- constant-prevalence Brier: **0.2200998264**.

The fresh Brier score is slightly worse than the constant-prevalence baseline, so probability calibration is not supported on this sample.

Frozen H1 close-position-only comparator:

- AUC: **0.5267693400**;
- bootstrap 95% CI: **[0.4396683935, 0.6052541894]**.

Six-feature minus close-position-only AUC:

- point difference: **+0.0113683422**;
- bootstrap 95% CI: **[-0.0540934838, +0.0675663523]**.

Thus the fresh sample does not establish that the six-feature geometry model materially outperforms close-position alone.

Legacy descriptive subset `FIRST_BULL close_pos >= 0.70`:

- N: **338**;
- TP1 positive rate: **33.4320%**.

`range_v` univariate AUC: **0.5333458224**.

## 8. Scientific interpretation

The fresh test does **not** demonstrate that bullish geometry has zero information. Both primary point estimates are directionally positive:

- AUC = 0.538 > 0.50;
- high-score minus low-score TP1 rate = +6.85 pp.

However, both preregistered whole-session confidence intervals cross their null values. Therefore the historical `MULTIVARIATE_REJECTION_GEOMETRY` finding is **not confirmed strongly enough by this partial fresh August sample to promote a replacement trigger**.

This is a failure of prospective confirmation, not evidence that a single 70% close-position threshold is scientifically correct.

## 9. Decision

The frozen preregistered decision is applied exactly:

`RETAIN_BR70_LEGACY_E_SCORE_LINEAGE_NO_NATURAL_70PCT_CLAIM`

Consequences:

1. `BR70` may remain only as the **legacy trigger required by the already-validated E-score lineage**.
2. We must **not** claim that 70% is a natural candle-rejection threshold; the historical threshold study did not support that claim.
3. `FIRST_BULL + continuous geometry` is **not promoted** from this fresh holdout.
4. The old `E_BUY_US` model must **not** be reused for a threshold-free FIRST_BULL trigger.
5. **No Pine modification is authorized** by this study.
6. No post-hoc threshold change to 75%, 80%, 85%, etc. is justified by this result.

## 10. Next scientifically valid step

If this line of research is continued, the candidate must remain frozen and be evaluated on **additional genuinely future US data** under a new prospective continuation preregistration. The purpose would be to increase independent session count and precision, not to tune the model after this failure.

The current partial-month sample ends at 2026-08-20 23:58 UTC. Any continuation should begin strictly after the already-opened source interval, maintain the same FIRST_BULL definition and frozen H1 model, and predefine whether evidence is evaluated incrementally or only after a fixed additional sample size.
