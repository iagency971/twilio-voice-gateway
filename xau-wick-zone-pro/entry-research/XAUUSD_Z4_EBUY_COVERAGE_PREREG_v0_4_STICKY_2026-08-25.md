# XAUUSD Z4 — E-BUY COVERAGE preregistration v0.4 STICKY

**Frozen:** 2026-08-25 after v0.3A engineering diagnostic; no reaction/trade outcome has been opened.  
**Scope:** BUY-only causal entry-location engineering gate.

## Methodological repair basis

The v0.3 full architecture crossed every frozen coverage/count/distance threshold but failed the original raw persistence threshold. The preregistered v0.3A diagnostic showed that 95.27% of raw non-matches were zones legitimately crossed below or no longer local at t+5. Among zones still eligible to survive, underlying state presence was 99.63%; only 49 of 26,580 transitions were unexplained disappearances. A further 620 transitions were underlying candidates still present but omitted from the displayed top-3.

Therefore v0.4 does **not** lower the stability threshold and does **not** modify any zone generator. It repairs the displayed top-3 and the persistence denominator so that legitimate invalidation/local-band exit is not mislabeled as instability.

## Fixed architecture — no search

Exactly one architecture is evaluated:

`Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`

All generator definitions and parameters are frozen from v0.3. No alternative architecture/configuration is tested.

Population remains frozen Dukascopy XAUUSD BID Jan-Jul 2024, mature C5 snapshots, New York 08:00–17:00, at least one causal Z4 above current close, TR60 normalization, local band 2.0v.

## Sticky displayed pool

The underlying current candidate union is generated exactly as in v0.3. Z4 retains de-duplication priority. Cross-family de-duplication uses the existing overlap / center-distance <=0.20v rule.

At each eligible snapshot:

- maximum displayed zones = 3;
- if there is no immediately preceding eligible snapshot exactly five minutes earlier, initialize with the three nearest de-duplicated current candidates;
- otherwise process each previously displayed zone in its existing slot order:
  - drop it if any confirmed M1 close in `(t-5,t]` is strictly below its previous frozen `zlo`;
  - drop it if its previous center is not strictly below current close or is farther than 2.0 current v;
  - otherwise, if a matching current underlying candidate exists (overlap or center distance <=0.25*max(v_prev,v_now)), carry that matched current candidate forward and remove it from the refill pool;
  - if no matching underlying candidate exists, the slot is released; no obsolete zone is fabricated or force-carried.
- fill released/empty slots from the nearest remaining current candidates until three are displayed;
- carried zones have priority over newly filled zones; no distance-based forced replacement is introduced in v0.4.

This rule is causal and deterministic. It addresses only top-3 churn; it cannot rescue a generator disappearance.

## Coverage/count/distance gate — unchanged

PASS still requires:
- coverage >=80% inside 1.0v;
- coverage >=90% inside 1.5v;
- coverage >=95% inside 2.0v;
- candidate-count median 1–3;
- candidate-count p90 <=3;
- nearest-candidate p90 <=1.50v.

## Corrected stability gate

Raw one-step display persistence is still reported for continuity but is no longer a gate because v0.3A demonstrated that its denominator includes legitimate terminal transitions.

For each displayed zone at t with an eligible t+5 snapshot, classify with the frozen v0.3A priority:
`MATCHED_DISPLAY`, `CROSSED_BELOW`, `NO_LONGER_LOCAL`, `UNDERLYING_PRESENT_NOT_DISPLAYED`, `UNEXPLAINED_DISAPPEARANCE`.

Define:

`survival_eligible_denominator = MATCHED_DISPLAY + UNDERLYING_PRESENT_NOT_DISPLAYED + UNEXPLAINED_DISAPPEARANCE`

`survival_aware_display_persistence = MATCHED_DISPLAY / survival_eligible_denominator`

The numerical threshold is retained from the original gate:
- survival-aware display persistence >= **70%**.

Additional hard guard:
- unexplained disappearance share of survival-eligible transitions <= **5%**.

No price reaction, profitability or destination outcome enters this stability measure.

## Verdict

`EBUY_COVERAGE_PASS_V04_STICKY` only if all unchanged coverage/count/distance checks and both corrected stability checks pass.

A PASS freezes the displayed E-BUY zone architecture and authorizes a **separate preregistered reaction/entry-quality study**. It does not claim that touching an E-BUY zone is profitable or produces support.

A FAIL prohibits reaction testing until another outcome-blind architecture/stability preregistration.

## Forbidden information

No future upper-Z4 hit, MFE/MAE, favorable/adverse excursion, reaction/rejection, TP/SL, RR, P&L, win rate, future return, or end-of-session route outcome may be used.