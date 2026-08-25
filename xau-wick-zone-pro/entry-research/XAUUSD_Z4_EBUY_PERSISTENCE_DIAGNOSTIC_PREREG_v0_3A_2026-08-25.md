# XAUUSD Z4 — E-BUY persistence diagnostic prereg v0.3A

**Frozen:** 2026-08-25 after v0.3 coverage result was opened.  
**Scope:** engineering diagnosis only; BUY-only; no reaction/trade outcome.

## Why this diagnostic exists

E-BUY coverage v0.3 crossed every frozen density/proximity/count threshold in its full architecture but failed the original raw one-step persistence threshold. The raw v0.1 metric counts every displayed zone at t as a persistence denominator whenever the next eligible snapshot is exactly five minutes later, and counts success only if an overlapping/near zone is still in the next displayed top-3.

That metric intentionally did not distinguish:
- a zone that was crossed/invalidated during the five-minute interval;
- a zone whose center is no longer a local BUY candidate at t+5 because it is above price or farther than 2v;
- a still-present underlying candidate displaced from the displayed top-3 by another nearer candidate;
- a genuinely unexplained detector/state disappearance while the zone remains locally eligible.

This diagnostic decomposes those cases. It does **not** alter the v0.3 verdict and it does not authorize reaction testing by itself.

## Frozen architecture diagnosed

Use the fixed v0.3 full architecture only:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

The architecture is fixed because it is the v0.3 all-family architecture whose coverage metrics crossed the frozen coverage/count/distance thresholds. No alternative architecture or parameter is selected in this diagnostic.

Population, data and causal Z4 reconstruction remain identical to v0.3: frozen Dukascopy BID Jan-Jul 2024, mature C5, New York 08:00–17:00, at least one causal Z4 above current close, max local band 2v.

## Per-zone transition classification

For each displayed zone at snapshot t when the next eligible snapshot is exactly t+5 minutes, classify in this priority order:

1. **MATCHED_DISPLAY** — an overlapping displayed t+5 zone exists, or center distance <= 0.25*max(v_t,v_t+5).
2. **CROSSED_BELOW** — if not matched, at least one confirmed M1 close in (t,t+5] is strictly below the t-zone zlo.
3. **NO_LONGER_LOCAL** — if not matched/crossed, at t+5 the old center is not strictly below current close or its old-center distance is >2.0*v_{t+5}.
4. **UNDERLYING_PRESENT_NOT_DISPLAYED** — if still local, a matching zone exists in the full pre-top3 candidate union at t+5 but was removed by dedup/top-3 display selection.
5. **UNEXPLAINED_DISAPPEARANCE** — none of the above.

The full pre-top3 union uses the same fixed families and their already frozen per-family max outputs; no new zone generator is introduced.

## Reported diagnostics

Report counts and shares over the original raw persistence denominator, plus:

- `raw_display_persistence = MATCHED_DISPLAY / total` (must reproduce the v0.3 value within floating tolerance);
- `survival_eligible_denominator = MATCHED_DISPLAY + UNDERLYING_PRESENT_NOT_DISPLAYED + UNEXPLAINED_DISAPPEARANCE`;
- `survival_eligible_state_presence = (MATCHED_DISPLAY + UNDERLYING_PRESENT_NOT_DISPLAYED) / survival_eligible_denominator`;
- `unexplained_share_of_survival_eligible = UNEXPLAINED_DISAPPEARANCE / survival_eligible_denominator`;
- `display_churn_share_of_survival_eligible = UNDERLYING_PRESENT_NOT_DISPLAYED / survival_eligible_denominator`.

## Interpretation rule frozen before diagnostic output

This is diagnostic, not a PASS gate. The next methodological repair is chosen by category dominance:

- if `UNDERLYING_PRESENT_NOT_DISPLAYED` is the largest non-matched survival-eligible category, preregister a sticky display-pool repair while keeping generators frozen;
- if `UNEXPLAINED_DISAPPEARANCE` is the largest non-matched survival-eligible category, diagnose generator/state identity before any reaction study;
- if `CROSSED_BELOW + NO_LONGER_LOCAL` account for the majority of all raw non-matches and survival-eligible state presence is >=70%, preregister a survival-aware persistence gate rather than lowering the raw threshold;
- otherwise no reaction study is authorized and a new zone architecture is required.

## Forbidden information

No future Z4 destination hit, MFE/MAE, favorable/adverse excursion, reaction/rejection, TP/SL, RR, P&L, win rate or future-return value may be computed, opened or used.