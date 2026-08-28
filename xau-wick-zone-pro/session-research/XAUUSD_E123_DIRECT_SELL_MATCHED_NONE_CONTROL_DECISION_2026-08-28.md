# XAUUSD direct E1/E2/E3 SELL — matched non-E control decision

Date: 2026-08-28  
Branch: `agent/xau-wick-zone-pro-dev`  
Status: **INCREMENTAL E-CONTACT NOT ESTABLISHED — Z4 GEOMETRY / BEARISH REJECTION EXPLAINS THE ROBUST EDGE**

## Frozen control design

This control was preregistered before reading any non-E control outcomes in:

`XAUUSD_E123_DIRECT_SELL_MATCHED_NONE_CONTROL_PREREG_v1_0_2026-08-28.md`

Prereg blob: `71f52ff66a4f44070e616746d41bfe3d155376fa`.

Frozen control engine blob: `b51be938006fa3d3193e52d257364cdd519c2bc4`.

Treated direct-E trades were not recomputed or altered; they came from immutable run `33193034282`.

Control workflow run: `33202072805`.

The control pool consisted of bearish BR70 rejections in the same session/Z4 geometry that did **not** touch any current causal displayed SELL E1/E2/E3. Matching used no outcomes and required same session-day, same geometry, same structural target Z4 and trigger time within 180 minutes. The matched control received exactly the treated trade's stop distance in local-volatility units, removing stop-budget design as a confounder.

Primary question: `BETWEEN_Z4_STRICT`, all E1/E2/E3 pooled.

## Primary aggregate result — BETWEEN_Z4_STRICT

Matching coverage is extremely high, so the conclusion is not driven by a small matched subset:

- H1 treated: 11,484; matched: 10,833; coverage **94.33%**;
- H2 treated: 11,980; matched: 11,288; coverage **94.22%**.

After excluding same-M1 ambiguous pairs from the outcome contrast:

| Window | Matched pairs | E conservative R | Non-E control R | E − control | E TP probability | Control TP probability | TP delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| H1 | 10,788 | +0.649R | +0.695R | **-0.046R** | 26.68% | 26.91% | -0.23 pp |
| H2 | 11,227 | +0.597R | +0.661R | **-0.065R** | 27.18% | 28.09% | -0.91 pp |
| Pooled | 22,015 | +0.622R | +0.678R | **-0.056R** | 26.94% | 27.51% | -0.58 pp |

Cluster bootstrap by session-day, 2,000 draws, seed 20260828:

- H1 delta-R 95% CI: **[-0.226 ; +0.108]R**;
- H2 delta-R 95% CI: **[-0.343 ; +0.140]R**;
- pooled delta-R 95% CI: **[-0.212 ; +0.078]R**;
- H2 TP-probability delta 95% CI: **[-1.82 ; -0.02] percentage points**.

The prespecified incremental-E gate therefore fails decisively:

- H1 matching coverage >=50%: PASS;
- H2 matching coverage >=50%: PASS;
- H1 E-control delta R >0: **FAIL**;
- H2 E-control delta R >0: **FAIL**;
- pooled bootstrap lower bound >0: **FAIL**;
- H1 TP delta non-negative: **FAIL**;
- H2 TP delta non-negative: **FAIL**.

## Session replication — BETWEEN_Z4_STRICT

| Session | H1 E-control R | H2 E-control R | Direction |
|---|---:|---:|---|
| US | -0.075R | +0.115R | reverses |
| Asia broad 18-03 | **-0.197R** | -0.009R | control >= E both halves |
| Asia Core 21-03 | -0.066R | **-0.237R** | control > E both halves |
| Europe 03-08 | +0.268R | **-0.220R** | reverses |

Six of the eight session x half cells favor the matched non-E control. The two positive E deltas do not replicate in the same session across H1/H2.

## Secondary result — ABOVE_HIGHEST_Z4_STRICT

The same conclusion holds above the highest Z4.

| Window | E conservative R | Non-E control R | E − control | TP delta |
|---|---:|---:|---:|---:|
| H1 | +0.331R | +0.390R | **-0.059R** | -1.91 pp |
| H2 | +0.501R | +0.473R | +0.027R | -0.80 pp |
| Pooled | +0.409R | +0.428R | **-0.019R** | -1.40 pp |

Pooled delta-R bootstrap 95% CI: **[-0.116 ; +0.086]R**. Pooled TP-probability delta CI is negative: approximately **[-2.31 ; -0.49] pp**.

Thus E contact is not supported as an incremental predictor here either.

## E-rank descriptive diagnostic

This was preregistered as descriptive only and cannot be used to optimize after the result.

Inside `BETWEEN_Z4_STRICT`:

- E1: delta R H1 **+0.066R**, H2 **+0.060R**, but TP delta is negative in both halves;
- E2: delta R H1 **-0.285R**, H2 **-0.587R**;
- E3: H1 approximately flat **-0.003R**, H2 **+0.602R**, a large H1/H2 instability.

The all-rank primary result fails, and no E-rank rule is promoted from this post-outcome descriptive split. E1 may warrant a separately frozen future question, but it is not validation.

## Matching QA

The matched sample is close on the prespecified covariates:

- median E/control trigger-time difference: **15 minutes**;
- median absolute target-distance difference: about **0.25 local-volatility units** between Z4;
- median absolute BR70 close-position difference: about **0.07**.

With >94% primary matching coverage and >22,000 non-ambiguous BETWEEN-Z4 matched pairs pooled, lack of incremental E evidence is not a small-sample problem.

## Scientific interpretation

The earlier direct-E study was real in the sense that E-triggered SELLs between Z4 had positive structural expectancy. But this control shows that **the positive expectancy is not specific to touching E1/E2/E3**.

Comparable bearish rejections **without E contact**, in the same Z4 geometry and with the same normalized risk budget, perform at least as well overall and frequently better.

Therefore the robust historical component is better described as:

**bearish rejection inside a causal Z4 gap + favorable distance to the lower Z4 target**

rather than:

**bearish rejection on an E zone**.

This is an important simplification: E1/E2/E3 should not currently be treated as a necessary predictive condition for this SELL concept.

## Critical practical limitation

The matched non-E control is an identification experiment, **not yet a directly tradable strategy**. Its stop distance was borrowed from the matched E trade in local-volatility units specifically to isolate the predictive value of E contact.

Therefore the next practical research question is not another E filter. It is to define, before outcomes, a fully causal standalone stop/invalidation for a generic `BETWEEN_Z4_STRICT + BR70` SELL — preferably a structural rule tied to the adjacent upper Z4 — and test that rule without using E at all.

No Pine or production rule is changed by this control.

Production authorization: **NONE_CONTROL_STUDY_ONLY**.
