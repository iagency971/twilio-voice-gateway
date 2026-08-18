# XAUUSD Phase C — Vantage RAW execution recalculation spec

Frozen before reading any recalculated P&L.

## Scope
This recalculation does not redo Phase A zone discovery or Phase B behavior classification. It only replaces the broker execution/cost layer used by Phase C.

## Historical price path
- Dukascopy XAUUSD M1 mid OHLC remains the historical price path.
- Dukascopy historical BID/ASK is not used as the Vantage execution spread in this recalculation.
- Zone generation, sigma60, contact detection, stacking and behavior labels remain unchanged.

## Synthetic Vantage RAW execution overlay
For fixed spread `s`:
- open_bid = open - s/2; open_ask = open + s/2
- high_bid = high - s/2; high_ask = high + s/2
- low_bid = low - s/2; low_ask = low + s/2
- close_bid = close - s/2; close_ask = close + s/2
- spread = s

This is an execution sensitivity model, not a claim that historical Vantage spread was constant minute by minute.

## Frozen cost scenarios
Primary: spread 0.11 USD, commission 6 USD round-turn / 100 oz lot.
Sensitivities: spread 0.10 and 0.12 USD, commission 6 USD RT.
Stress: spread 0.18 USD, commission 9 USD RT.

The 6 USD figure is the current Vantage RAW ECN Precious Metals round-turn commission. Spread is variable in reality; 0.10–0.12 USD is treated as an observed operating range and tested as scenarios.

## Entry models
Structural models rerun unchanged:
- PASSIVE_TOUCH
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTANCE_RETEST
- RECLAIM_PULLBACK

Raw TOUCH_NEXT_OPEN without a risk floor is audit-only because the 2013 diagnostic found near-zero risk geometry. TOUCH_NEXT_OPEN is recalculated only with the already-frozen floors k = 0.25, 0.50, 0.75, 1.00 using risk = max(structural_risk, k * causal_sigma60). The complete k grid is retained; no k is selected after seeing results.

## Target surface
R = 0.5, 1.0, 1.5, 2.0, 2.5, 3.0. Same 120-minute horizon and adverse same-bar ambiguity rule.

## Decision gate
Primary scenario 0.11 + 6 USD:
1. total trades >= 300
2. weighted average net R > 0
3. annual median net R > 0
4. >= 10/15 positive years
5. median annual PF > 1.0

Stress scenario 0.18 + 9 USD:
6. weighted average net R > 0
7. >= 8/15 positive years

Neighboring-R stability is required. For TOUCH_NEXT_OPEN, neighboring-k stability is also required. An isolated k/R optimum is not accepted.

## Interpretation
Passing this recalculation only nominates a price-only Vantage-execution candidate. It does not replace the still-missing long-history COMEX/GC volume/order-flow layer and is not live validation.
