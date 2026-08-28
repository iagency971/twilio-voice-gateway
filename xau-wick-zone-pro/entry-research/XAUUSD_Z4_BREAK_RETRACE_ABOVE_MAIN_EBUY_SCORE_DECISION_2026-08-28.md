# XAUUSD Z4 breakout→retrace ABOVE_MAIN — E_BUY_US score decision

Date: 2026-08-28

## Final classification

**`E_SCORE_MAPPING_INSUFFICIENT`**

No E threshold is promoted. No Pine or production-rule modification is authorized from this interaction study.

## Frozen design

Preregistration:
`XAUUSD_Z4_BREAK_RETRACE_ABOVE_MAIN_EBUY_SCORE_PREREG_v1_0_2026-08-28.md`

Preregistration commit: `8e21016fd2264deb5f0697619c91c7c793f95fdb`

Structural setup was unchanged:
- US only, 08:00–17:00 `America/New_York`;
- bullish confirmed-M1 break of causal main Z4;
- mandatory post-breakout wick-or-more retrace into main Z4;
- E1/E2/E3 may lie anywhere relative to main Z4;
- wick below main_zlo allowed;
- only M1 close below main_zlo invalidates;
- BULL_REJECTION legacy trigger (`close>open`, close-position >=0.70);
- entry next M1 open;
- TP at frozen next-higher causal Z4 lower bound;
- primary subgroup `ABOVE_MAIN`, meaning the triggering E zone lies fully above the main Z4 (`E.zlo > main.zhi`).

Frozen structural engine blob:
`7862638917015838948001a374f9bea7dba83e07`

Frozen score:
- `E_BUY_US` v1.1;
- `M1_LOGISTIC`;
- model SHA-256 `ac1c3effe84b64ffd1deebd82c3c6009ae56be9505974e3824b20169e3b38342`;
- percentile/rank in frozen H1 training-score CDF, not a calibrated probability;
- no refit or recalibration.

H1 uses official M1_LOGISTIC OOF scores only. H2 uses the official frozen-H1-model scored table.

## Execution evidence

Workflow run: `33166971466` — SUCCESS.
Artifact: `z4-above-main-ebuy-score-v1-0`.
Artifact digest: `sha256:e06d234825832b1766c96f5b84ca663c099afb7b4fedf52dfc2bb1abb4ed2354`.

Result SHA-256:
`94d814a7da0b7c624f39518e13724a0178fe997ac1674cec099e068a67251183`

Mapped-event table SHA-256:
`d8f59b439c598e1bee1048aaf156f3aa17080a376e9ebc1d70a35b445a80d326`

## Mapping gate

The critical result is that the structural setup and the official E-BUY score universe overlap only partially.

### H1 OOF

- historical terminal `ABOVE_MAIN`: 42;
- OOF-time-eligible structural terminals (2024-12-01 onward): 30;
- Aug–Nov 2024 unavailable by design because no OOF score exists: 12;
- unique exact official-score matches: **12 / 30 = 40.0%**;
- eligible no-match: 18;
- ambiguous multi-match: 0.

### H2 frozen model

- historical terminal `ABOVE_MAIN`: 32;
- score-time eligible: 32;
- unique exact official-score matches: **8 / 32 = 25.0%**;
- no-match: 24;
- ambiguous multi-match: 0.

The preregistered mapping rule requires at least 20 uniquely score-matched H2 terminal trades. H2 has only 8.

Therefore the precedence classification is **`E_SCORE_MAPPING_INSUFFICIENT`**.

This matters conceptually: the prior structural runner allows a rejection after the main-Z4 retrace whenever a displayed E is touched, whereas the official `E_BUY_US` score exists only for observations that also satisfy the frozen official E-BUY episode/contact/arming pipeline. A synthetic score was intentionally not created for structural trades outside that official universe.

## H1 OOF score results — matched subset only

N = 12 terminal trades:
- TP = 7;
- invalidation = 5;
- baseline TP rate = **58.33%**;
- continuous AUC = **0.5429**;
- session-cluster bootstrap 95% AUC interval = **[0.1774, 0.8857]** (9,984 valid / 10,000 reps);
- median E for TP = **54.51**;
- median E for invalidation = **58.08**.

The continuous signal is therefore weak and highly uncertain in H1 OOF; importantly, losing trades actually have a slightly higher median E than winning trades in this tiny subset.

### Fixed cumulative H1 OOF bands

| E band | N | TP | Invalid. | TP rate | Structural expectancy before costs |
|---|---:|---:|---:|---:|---:|
| All scored | 12 | 7 | 5 | 58.33% | +0.012R |
| E>=50 | 8 | 5 | 3 | 62.50% | -0.020R |
| E>=60 | 5 | 3 | 2 | 60.00% | -0.083R |
| E>=70 | 3 | 2 | 1 | 66.67% | -0.096R |
| E>=80 | 1 | 1 | 0 | 100% | +0.311R |
| E>=90 | 0 | 0 | 0 | n/a | n/a |

There is no usable monotonic threshold evidence here. E80/E90 are far too sparse.

## H2 frozen-model score results — matched subset only

N = 8 terminal trades:
- TP = **8**;
- invalidation = **0**;
- baseline TP rate = **100%**;
- structural expectancy before costs = **+0.818R**.

Because every matched H2 observation is a winner, ROC AUC and rank/outcome correlation are mathematically undefined. The score level cannot discriminate winners from losers when the matched set contains no losers.

### Fixed cumulative H2 bands

| E band | N | TP | Invalid. | TP rate | Structural expectancy before costs |
|---|---:|---:|---:|---:|---:|
| All scored | 8 | 8 | 0 | 100% | +0.818R |
| E>=50 | 6 | 6 | 0 | 100% | +0.658R |
| E>=60 | 4 | 4 | 0 | 100% | +0.637R |
| E>=70 | 2 | 2 | 0 | 100% | +0.187R |
| E>=80 | 2 | 2 | 0 | 100% | +0.187R |
| E>=90 | 1 | 1 | 0 | 100% | +0.299R |

These figures **do not show that E80 or E90 is better**. They show that all eight officially score-eligible H2 `ABOVE_MAIN` structural trades won, including low/moderate E scores. The E threshold itself adds no measurable discrimination in this sample.

## Descriptive pooled matched subset — not a primary preregistered inference

Across H1 OOF + H2 score-matched terminal trades:
- all scored: 15/20 TP = **75.0%**;
- E>=50: 11/14 = **78.57%**;
- E>=60: 7/9 = **77.78%**;
- E>=70: 4/5 = **80.0%**;
- E>=80: 3/3 = **100%**;
- E>=90: 1/1 = **100%**.

The high-score tail is much too sparse to infer a cutoff, and the intermediate bands do not show a meaningful monotonic improvement.

## Post-outcome diagnostic: score eligibility itself

This diagnostic was **not** the preregistered primary question and cannot be promoted from these data.

Among score-time-eligible H1 OOF structural `ABOVE_MAIN` trades:
- official-score matched: 7/12 TP = 58.33%;
- official-score unmatched: 10/18 TP = 55.56%.

No meaningful difference appears in H1 OOF.

In H2:
- official-score matched: **8/8 TP = 100%**;
- official-score unmatched: **14/24 TP = 58.33%**.

This H2 contrast is striking, but it is not replicated in H1 OOF. It suggests a separate future hypothesis: the **official E-BUY episode/contact/arming eligibility** may itself interact with the structural `ABOVE_MAIN` setup more strongly than the numeric E rank. That question requires its own preregistration and genuinely new evidence; it is not evidence that E80/E90 should be used now.

## Decision

1. **Do not apply E>=50/60/70/80/90 as a new filter to `ABOVE_MAIN` from this study.**
2. **Do not claim that higher `E_BUY_US` improves the structural setup.** H1 OOF continuous evidence is weak; H2 cannot estimate discrimination because all eight matched observations are winners.
3. **Do not synthesize E scores for the 60–75% of structural trades that fall outside the official score universe.** That would change the score definition.
4. Keep `ABOVE_MAIN` as a research candidate, but the existing numerical E rank does not currently provide a scientifically established additional cutoff.
5. The most interesting new candidate is not a threshold; it is `ABOVE_MAIN + official E-BUY eligibility`. This is a new post-outcome hypothesis and must be tested separately before any Pine/production use.

Current authorization:

`NO_E_THRESHOLD_PROMOTION_MAPPING_INSUFFICIENT`
