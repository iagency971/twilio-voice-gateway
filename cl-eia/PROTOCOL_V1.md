# CL Intraday Momentum + EIA Regime V1

Status: `PREOUTCOME_FROZEN_COST_PROBE_ONLY`
Branch: `agent/cl-eia-intraday-momentum-v1`

## External evidence basis
This is a **new CL-futures transposition**, not an exact replication of the papers below.

1. Wen et al., *Intraday momentum and return predictability: Evidence from the crude oil market*, Economic Modelling 95 (2021), 374-384. USO 1-minute data, 2006-2018. The first half-hour return predicts the last half-hour return and a sign-based market-timing strategy is profitable.
2. Wen, Indriawan, Lien & Xu, *Intraday Return Predictability in the Crude Oil Market: The Role of EIA Inventory Announcements*, The Energy Journal 44(5) (2023), 149-172; public working-paper version available in 2021. On EIA days, the 10:30-11:00 ET return becomes the efficient predictor of the last half-hour; on non-EIA days the first half-hour remains the efficient predictor. Their market-timing rule is long the last half-hour when the predictor is positive and short when negative.

The published work uses USO regular trading hours 09:30-16:00 ET. For prop-firm relevance this protocol pre-registers a CL futures RTH translation before opening any CL outcomes.

## Frozen CL translation
Instrument: NYMEX WTI Crude Oil futures, Databento continuous `CL.v.0`, `GLBX.MDP3`, OHLCV-1m.
Timezone: America/New_York.

CL RTH proxy window: 09:00-14:30 ET.

### Non-EIA days
- Predictor = CL return from 09:00 open to 09:29 close (first 30 minutes of CL RTH).
- At 14:00 open: LONG if predictor > 0, SHORT if predictor < 0, no trade if exactly zero.
- Exit = 14:29 close.

### Standard EIA announcement days
- Only official EIA Weekly Petroleum Status Report releases occurring at 10:30 ET are classified as EIA events.
- Predictor = CL return from 10:30 open to 10:59 close.
- At 14:00 open: LONG if predictor > 0, SHORT if predictor < 0, no trade if exactly zero.
- Exit = 14:29 close.

### Holiday-shifted EIA releases
If the official EIA report is released at a non-standard day/time (e.g. holiday delay), that session is excluded from V1 rather than inventing a shifted rule after outcomes.

One trade maximum per day. No stop, TP, volatility filter, direction filter, weekday filter, news-surprise input, or threshold.

## Information causality
All predictors are fully completed before 14:00. Entry uses the 14:00 minute OPEN; no same-bar close fill.

## Cost model
Edge test first, before any prop sizing overlay.
CL point value: $1,000 per 1.00 point; tick 0.01 = $10.
PRIMARY friction: $30 round turn per 1 CL contract (fees + 1 tick adverse slippage per side equivalent).
STRESS friction: $50 round turn per 1 CL contract.
Net points = signed exit-entry points - cost_usd/1000.

## Time split
Because the public EIA working paper was available in 2021, use only later CL futures data:
- Main post-publication persistence: 2021-09-01 through 2025-12-31.
- Current holdout: 2026-01-01 through latest complete historical session, reported separately.
No parameter fitting is permitted on either period.

## Predeclared gates
### Non-EIA daily engine
Required on 2021-09 through 2025:
1. >= 750 trades.
2. PRIMARY mean net points/trade > 0.
3. PRIMARY PF >= 1.05.
4. At least 3 positive calendar years.
5. STRESS mean > 0.
6. Remove best 5% of trades: remaining mean >= 0.

### EIA accelerator
Required on 2021-09 through 2025:
7. >= 120 standard 10:30 EIA events.
8. PRIMARY mean net points/trade > 0.
9. PRIMARY PF >= 1.15.
10. At least 3 positive calendar years with EIA events.
11. STRESS mean > 0.
12. Remove best 10% of EIA trades: remaining mean >= 0.

### 2026 persistence
At least one of the two engines must remain positive in PRIMARY and STRESS during 2026; no 2026 result may be used to change the rules.

Terminal states:
- both engines pass + 2026 persists: `CL_V1_PASS_FOR_RISK_OVERLAY_RESEARCH`;
- only EIA passes: `CL_EIA_ACCELERATOR_PASS_ONLY`;
- only non-EIA passes: `CL_DAILY_MOMENTUM_PASS_ONLY`;
- otherwise: `CL_V1_NO_GO`.

## Stage 2 after a PASS only
Introduce a prop-compatible risk overlay without altering signal direction/timing. Candidate risk controls must be pre-registered separately (e.g. fixed-dollar emergency stop derived only from pre-entry volatility, MCL contract sizing, daily loss cap). The no-stop V1 edge test itself is not live-ready.

## Cost authorization policy
No Databento time-series request may be made from this branch until a free `metadata.get_cost()` estimate is committed and the user explicitly authorizes the estimated paid download.
