# XAUUSD Z4 / E-BUY — bullish reaction candle geometry decision v1.0

**Date:** 2026-08-27  
**Run:** GitHub Actions `33124587064`  
**Artifact:** `xau-z4-ebuy-bull-candle-geometry-v1-0-1`, digest `sha256:9b6d70594bae879b6702058c0b898ad39ce359f6a69646c304ece65946dfe314`  
**Result JSON SHA-256:** `f4bb396741e26745f3e675ed9a32501058c6d1f795dc855e39fc9ff9ef5df494`  
**Formal prereg classification:** `MULTIVARIATE_REJECTION_GEOMETRY`

## 1. Engineering/parity gate

The timestamp-only engineering repair was applied after the first workflow failed before producing interpretable outcomes.

The repaired run reproduced the incumbent 0.70 trigger **exactly**:

- H1 fired = 7,127 and TP1 resolved rate = 31.4390209593%;
- H2 fired = 7,643 and TP1 resolved rate = 30.1296320545%.

All four parity checks passed. Therefore the threshold-free geometry analysis is on the same reaction semantics as the validated incumbent BR research.

## 2. Direct answer on the 0.70 cutoff

The fixed descriptive wait-threshold curve is smooth and monotonic; there is no local break at 0.70.

### H1

| close-position threshold | fired share | TP1 resolved rate |
|---:|---:|---:|
| 0.50 | 46.62% | 29.63% |
| 0.55 | 45.84% | 30.05% |
| 0.60 | 44.97% | 30.43% |
| 0.65 | 43.75% | 30.83% |
| **0.70** | **42.18%** | **31.44%** |
| 0.75 | 40.31% | 32.11% |
| 0.80 | 37.98% | 32.99% |
| 0.85 | 34.93% | 33.86% |
| 0.90 | 31.05% | 34.83% |
| 0.95 | 25.27% | 35.58% |

### H2 retrospective replication

| close-position threshold | fired share | TP1 resolved rate |
|---:|---:|---:|
| 0.50 | 47.66% | 28.51% |
| 0.55 | 46.98% | 28.80% |
| 0.60 | 46.16% | 29.13% |
| 0.65 | 45.04% | 29.56% |
| **0.70** | **43.48%** | **30.13%** |
| 0.75 | 41.76% | 30.58% |
| 0.80 | 39.47% | 31.25% |
| 0.85 | 36.40% | 32.08% |
| 0.90 | 32.28% | 32.86% |
| 0.95 | 25.71% | 34.27% |

The progression through 0.70 is ordinary. For example H1 TP1-rate increments are +0.40 pp from .60→.65, +0.61 pp from .65→.70, +0.67 pp from .70→.75, +0.89 pp from .75→.80 and +0.86 pp from .80→.85. H2 is similarly smooth.

**Decision:** `0.70` is not supported as a natural structural cutoff. It remains an arbitrary prespecified operating point on a continuous frequency/quality trade-off.

## 3. Threshold-free FIRST_BULL baseline

With no close-position threshold, define the first confirmed bullish M1 after contact as the candidate.

- H1: N=8,239, resolved N=8,219, TP1 rate=28.64095%; median contact→trigger=1 minute.
- H2: N=8,773, resolved N=8,765, TP1 rate=27.52995%; median contact→trigger=1 minute.

Thus merely waiting for the first bullish candle already creates a viable reaction event, and progressively stronger candle geometry provides additional but continuous filtering information.

## 4. Close-position is informative but does not support a hard cutoff

`close_pos=(close-low)/(high-low)` on FIRST_BULL:

- H1 AUC = 0.54172;
- H2 retrospective AUC = 0.54127;
- H2 session-bootstrap 95% CI = [0.52734, 0.55678];
- H1 top-vs-bottom quintile TP1 difference = +8.17 pp;
- H2 top-vs-bottom quintile difference = +7.16 pp, 95% CI [3.85, 10.54] pp.

So close-position has real continuous information.

However H1's best binary change-point is ~0.81364 and its session-bootstrap distribution is broad:
- p10=0.71532;
- p25=0.75336;
- median=0.77528;
- p75=0.81818;
- p90=0.82791;
- p90-p10=0.11259;
- IQR=0.06482.

This fails the preregistered concentration gates.

Furthermore H1 session-blocked CV favors the continuous close-position model:
- continuous mean log loss = 0.59716;
- threshold model mean log loss = 0.59819.

The exact H1 point (~0.8136) does split H2 directionally (30.04% above vs 25.00% below; +5.04 pp, bootstrap 95% CI [3.25, 7.09] pp), but because the cutoff estimate is broad and the continuous model cross-validates better, the formal `STABLE_CLOSEPOS_CHANGEPOINT_CANDIDATE` criterion fails.

**Decision:** close-position should be treated as a continuous descriptor, not a 70/80/etc. Boolean truth.

## 5. What candle properties actually carry information?

Fixed single-feature H2 retrospective replication:

| Feature | H2 oriented AUC | 95% CI | H2 top-bottom quintile TP1 delta |
|---|---:|---:|---:|
| `range_v` | **0.5779** | **[0.5619, 0.5942]** | **+14.94 pp** |
| close vs `zhi` / zone width | 0.5597 | [0.5455, 0.5727] | +11.78 pp |
| close vs center / zone width | 0.5587 | [0.5445, 0.5719] | +11.42 pp |
| body fraction | 0.5473 | [0.5328, 0.5615] | +9.64 pp |
| close-position | 0.5413 | [0.5273, 0.5568] | +7.16 pp |
| log1p(lower-wick/body) | 0.5282 | [0.5144, 0.5421] | +5.06 pp |
| lower-wick fraction | 0.5120 | [0.4985, 0.5264] | +3.15 pp |

The strongest pure-candle descriptor is therefore **range normalized by contact volatility**, not lower-wick size.

The direction of `lower_wick/body` is negative: a larger lower wick relative to the bullish body is associated with lower, not higher, TP1 success in this sample. Lower-wick fraction alone is weak and its H2 AUC interval includes 0.50.

This does **not** support a classic “long lower wick = better rejection” rule.

## 6. Frozen 6-feature candle model

The preregistered H1-only L2 logistic model using close-position, body fraction, lower/upper wick fractions, lower-wick/body and range/v gives:

- H1 AUC = 0.58042;
- H2 retrospective AUC = 0.57956;
- H2 95% CI = [0.56575, 0.59368];
- H2 AP = 0.33679;
- H2 Brier = 0.19652;
- H2 close-position-only AUC = 0.54127;
- H2 AUC delta = +0.03828;
- delta bootstrap 95% CI = [+0.02478, +0.05185].

This passes the preregistered `MULTIVARIATE_REJECTION_GEOMETRY` classification gate.

### Important coefficient caveat

For a bullish candle, `close_pos`, `body_frac`, `lower_wick_frac` and `upper_wick_frac` are algebraically dependent. The L2 model remains valid for predictive comparison, but individual coefficients should not be interpreted causally or independently.

## 7. Post-hoc ablation diagnostic — not a preregistered selection result

A diagnostic performed only after the formal result shows that most of the multivariate gain is explained by `range_v`:

- range/v alone H2 AUC ≈ 0.57785;
- preregistered pure 6-feature model H2 AUC ≈ 0.57956;
- pure-6 minus range-only session-bootstrap AUC delta has 95% interval approximately [-0.0082, +0.0118].

A post-hoc model adding zone-relative reclaim geometry (`range_v`, body fraction, close-vs-zhi, penetration) reaches H2 AUC ≈0.5860, but its gain over range-only is also not yet conclusive: bootstrap delta interval approximately [-0.0026, +0.0184].

These post-hoc numbers **do not authorize model selection**. They are used only to interpret the formal finding and guide the next preregistration.

## 8. Scientific interpretation

The incumbent label `BULL_REJECTION` is too visually suggestive.

The data support a more precise description:

> after E-BUY contact, useful information is carried mainly by the strength/size of the bullish response relative to local volatility, plus body/close/reclaim geometry; there is no evidence for a privileged 70% close cutoff and little evidence that a long lower wick itself is the key mechanism.

This resembles a **bullish displacement / reclaim response** more than a classic pin-bar rejection.

## 9. Production decision

- Keep current Pine behavior unchanged for now so the already validated US E-score lineage is not silently broken.
- Do **not** promote 0.70 as a scientifically privileged threshold.
- Do **not** replace it with 0.80, 0.85, 0.90 or another grid winner.
- The next research cycle should remove the hard close-position gate, trigger on a threshold-free causal bullish response, and use continuous reaction geometry/context in a frozen score.
- A new specification must be frozen before a fresh US holdout is opened. H2 is already spent and cannot validate the replacement.

**Current scientific status:** incumbent BR70 remains an empirically validated legacy trigger for the existing E-score lineage, but its 70% cutoff is not a defensible final definition of rejection.