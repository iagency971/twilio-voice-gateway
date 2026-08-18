# XAUUSD Reaction Zone Research — Phase C NO_GO checkpoint

Date: 2026-08-18 UTC
Branch: `agent/xau-multiyear-research`

## 1. Frozen Phase C v2 aggregate

The complete 2011–2025 Phase C v2 aggregate contains 15 annual files and 144 `sample × entry_model × target_R` cells.

Frozen gate survivors: **0**.

Important diagnostic exclusion: raw `TOUCH_NEXT_OPEN` cells without a volatility risk floor are retained for audit only and MUST NOT be used for strategy selection. In 2013, one OBJECTIVE_LIQUIDITY_ONLY TOUCH_NEXT_OPEN trade had structural risk of only `0.0000528071` USD and produced approximately `-7574.74R`; the raw 2013 BID/ASK feed itself passed the independent range/gap/spread QA. The issue is the entry/stop geometry, not a corrupt price feed.

## 2. R2 RECLAIM_PULLBACK

R2 was preregistered and evaluated without changing the v1 models. It failed the frozen stability logic and is **NO_GO**. Do not rescue it by selecting an isolated RR after the fact.

## 3. S1 volatility-floor hypothesis

S1 rule was frozen before the S1 run:

`risk = max(structural_risk, k × causal_sigma60)`

It never tightens the structural stop.

The preregistered 2025 screen promoted only:

- sample: `DISPLACEMENT_ORIGIN_ONLY`
- entry: `TOUCH_NEXT_OPEN`
- `k = 1.0`
- RR: `1.0`, `1.5`, `2.0`

2025 net expectancy after the historical $22 RT/100oz cost sensitivity was only approximately:

- RR1.0: `+0.00498R`
- RR1.5: `+0.01190R`
- RR2.0: `+0.00159R`

All three remained slightly negative under 1.5x costs.

The 2011–2016 promoted-cell annual results are negative after $22 for all three RR. Therefore at least six of the fifteen years are already negative. The frozen S1 gate requires at least 10/15 positive years, leaving at most nine possible positive years. **S1 is therefore mathematically NO_GO regardless of 2017–2025.**

S1 did successfully remove the pathological near-zero-risk behavior: for example, 2013 minimum S1 risk was about `0.8503` USD rather than `0.0000528` USD. That is an execution-quality fix, not an edge.

## 4. Strongest non-pathological Phase C near-candidate

The strongest non-pathological cell in the complete Phase C v2 aggregate is:

`DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + RR1.5`

2011–2025 aggregate:

- total trades: `304`
- weighted avg gross R: `+0.14056`
- weighted avg net R after $22: `+0.03455`
- annual median net R after $22: `+0.05214`
- positive years after $22: `10/15`
- median annual PF net after $22: `1.09043`
- weighted avg net R at 1.5x costs: `-0.01845`
- positive years at 1.5x costs: `7/15`

It passes gates 1,2,3,4,7 and fails gates 5 and 6. Under the frozen protocol it is **NO_GO**, not a strategy candidate for live trading.

The neighboring RR2.0 remains positive after the base $22 sensitivity but loses annual stability and also fails the 1.5x cost gates. Therefore the RR1.5 result is not accepted as a robust survivor.

## 5. Scientific decision

No Phase C entry/stop/target configuration tested so far is validated for live trading.

Do NOT continue by scanning more RR values, adding breakeven rules, trailing stops, partial exits, or arbitrary filters to rescue the failed cells. That would turn the search into outcome-driven optimization.

The next conceptual audit should decide whether to proceed to a preregistered Phase D conditional model using causal features known by entry time, with particular attention to the low-frequency `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION` near-candidate, or whether the zone/behavior definitions themselves need revision first.

Any Phase D model must use strict chronological walk-forward evaluation, fixed feature availability rules, fixed model/hyperparameters before target-year evaluation, explicit costs, and later a genuinely prospective/virgin validation block. Historical 2011–2025 results are research data, not virgin OOS.
