# BTC Prop-Firm 15m Breakout Protocol V3

Status: PRE-OUTCOME / 2026 SEALED

## Objective
Move away from cost-sensitive 30-minute session effects and test a larger-excursion intraday trend architecture suitable for prop-firm risk sizing.

## Data / chronology
- Binance BTCUSDT spot, public 5m monthly klines, aggregated causally to 15m.
- Train: 2019-2022.
- DEV confirmation: 2023.
- Temporal validation: 2024-2025.
- 2026 MUST NOT be downloaded or inspected.

## Signal
At completed 15m bar t:
- LONG breakout if close[t] > max(high) of the previous L completed 15m bars.
- SHORT breakout if close[t] < min(low) of the previous L completed 15m bars.
- Entry at next 15m bar open t+1.
- ATR = Wilder-style 14-bar ATR known at t.
- Stop distance = 1.5 * ATR[t].
- Fixed target = 2.0R.
- Maximum holding time = 16 bars = 4 hours.
- One position at a time per candidate.
- If stop and target both trade inside the same bar, record stop first (conservative).
- Stop gaps exit at observed open; favorable target gaps are capped at target.

## Daily regime variant
Daily RSI(14) uses completed UTC daily closes only and is shifted one full day.
- LONG allowed only if prior-day RSI14 > 50.
- SHORT allowed only if prior-day RSI14 < 50.

## Exactly four candidates
- L16_RAW (4h Donchian lookback)
- L32_RAW (8h Donchian lookback)
- L16_RSI
- L32_RSI
No other lookback, stop, target, holding-time or indicator parameter is allowed in V3.

## Costs
- PRIMARY = 5 bp per side.
- STRESS = 10 bp per side.

## Governance
1. Candidate selection uses TRAIN 2019-2022 only.
2. Train eligibility: N>=250, mean>=+0.08R, PF>=1.15, >=3/4 positive years, maxDD<=20R.
3. Freeze the top eligible train candidate by score mean_R*sqrt(N). No second-choice substitution after confirmation.
4. Open 2023 only for the frozen candidate. Confirmation PASS: N>=40, mean>=+0.05R, PF>=1.10, positive 2023, maxDD<=10R.
5. Only on confirmation PASS open 2024-2025 for that frozen candidate. Validation PASS: N>=100, mean>=+0.08R, PF>=1.15, both years positive, maxDD<=12R; STRESS mean>0 and PF>1.05.
6. Only a validation PASS permits a separate freeze followed by one-time 2026 OOS and prop-challenge mapping.
