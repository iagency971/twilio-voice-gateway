# XAUUSD Reaction Zones — COMEX DEV_RANK1 PASSIVE_TOUCH Fill Result Freeze v1

Date: 2026-08-18
Status: FROZEN RESULT — NO PROMOTION FOR PASSIVE_TOUCH FILL PREDICTION

## Scope

This freeze applies only to the preregistered `PASSIVE_TOUCH` fill/re-entry probability target on DEV_RANK1. It does not make a global statement that COMEX is useless for all economic targets.

The monolithic fill job was cancelled by the GitHub 55-minute timeout. The result below was recovered with an exact 24-fold computation (8 outer years × B0/B1/B2), importing the same frozen scientific functions, features, regularization grid, nested LOYO rules and weights. No market-data call, new feature, hyperparameter or target definition was introduced by the recovery.

## Population

- decision events: 31,710
- raw filled/entered: 18,714
- raw fill rate: 59.0161%
- B2-causally-available primary comparison events: 30,525
- primary sessions: 92
- primary fills: 18,041
- primary non-fills: 12,484
- primary fill rate: 59.1024%
- years: 2011–2018

This is a genuinely informative binary target; unlike CLEAN_REJECTION / FAILED_AUCTION / TOUCH_NEXT_OPEN, the minority class is not vanishingly small.

## Primary results

### B1 vs B0 — GC M1 context added to XAU baseline

Family-balanced log-loss improvement: **-0.0135344724**
Population-event improvement: **-0.0122147861**
Session-balanced improvement: **-0.0117059442**
Positive outer years: **1 / 8**
Session-cluster bootstrap 95% interval: **[-0.0271497554, -0.0008867400]**
Directional gate: **FAIL**

Only 2012 was positive. The remaining seven outer years were adverse.

### B2 vs B1 — GC trades / auction features added

Family-balanced log-loss improvement: **-0.0463372759**
Population-event improvement: **-0.0178748879**
Session-balanced improvement: **-0.0176407402**
Positive outer years: **1 / 8**
Session-cluster bootstrap 95% interval: **[-0.0874450873, -0.0136234460]**
Directional gate: **FAIL**

Only 2017 was positive. The other seven outer years were adverse.

## Family diagnostics

The failure is not an artifact of the dominant FVG family alone.

B2 vs B1 population/session-balanced log-loss improvement was adverse for every listed family:

- CONFLUENCE: -0.05009 / -0.03628
- DOZ_ONLY: -0.02720 / -0.03376
- FVG_ONLY: -0.01663 / -0.01669
- MEMORY_ONLY: -0.12397 / -0.01638
- OBJECTIVE_ONLY: -0.01379 / -0.01282

B1 vs B0 was also adverse in the primary/session-balanced view. Very small positive population-only deltas for DOZ_ONLY and MEMORY_ONLY do not survive session balancing and cannot be promoted.

## Decision

**NO-GO for using the frozen DEV_RANK1 B1 or B2 COMEX feature groups to predict PASSIVE_TOUCH fill probability.**

Do not retune the reaction/contact window, feature definitions, C grid, family weights, decision time, or model class to rescue this target in DEV_RANK1.

This result does **not** decide the separate filled-trade `net_R` target. COMEX could still, in principle, add information about the economic outcome conditional on a fill even though it does not improve fill prediction itself. That question remains separately preregistered and must use the already-frozen net-R surface.

Source result:
`xau-final-results/comex_dev_rank1_fill_model_passive_touch_v1/result.json`
