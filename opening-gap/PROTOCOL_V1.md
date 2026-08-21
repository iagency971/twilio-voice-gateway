# ES/SPY Opening-Gap Reversal V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/es-opening-gap-reversal-v1`

## External hypothesis
Grant, Wolf & Yu (Journal of Banking & Finance, 2005) document significant intraday reversal in S&P 500 futures after large opening price changes. Their reported event filter is ±0.20%. They find approximately 10 minutes of continuation after the open, followed by a long sequence of significant reversals. The paper also warns that transaction costs materially weaken gross profitability.

V1 translates that published pattern into a single executable rule before looking at post-publication outcomes.

## Frozen rule
Event definition:
- Opening gap = current RTH 09:30 open / previous complete RTH close - 1.
- Event if absolute gap >= 0.20%.
- Both positive and negative gaps included; no day-of-week or sign filter.

Execution:
- Wait exactly 10 minutes after the 09:30 open.
- Entry at 09:40 open.
- Fade the opening gap: gap UP -> SHORT; gap DOWN -> LONG.
- Exit at 10:40 open, exactly 60 minutes after entry.
- One trade per event day.
- No stop, target, trailing logic, or discretionary filter in Stage 1.

## SPY post-publication persistence test
Data: public `BrianWeiss1/StockList/5min_data_SPY_2015_to_2024.csv`.
Evaluation: all executable event days from 2015-01-01 through 2024-12-31, entirely after the original 2005 paper.
- Prior close = prior day's 15:55 5-minute bar close (price at 16:00).
- Open = current day's 09:30 bar open.
- Entry = 09:40 bar open.
- Exit = 10:40 bar open.
- PRIMARY cost = 2 bps round-turn.
- STRESS cost = 5 bps round-turn.

## Direct ES current test
Data: public `axb0306/cme-futures-ohlc`, `ES/ES_1min_20260120_20260415.csv`.
- Timestamps UTC -> America/New_York.
- Prior close = previous complete RTH 15:59 close.
- Open = current 09:30 open.
- Entry = 09:40 open.
- Exit = 10:40 open.
- 1 ES contract, $50/point.
- PRIMARY friction = $30 round-turn.
- STRESS friction = $55 round-turn.

## Predeclared gates
### SPY structural persistence — all required
1. >= 150 executed events.
2. PRIMARY mean net return > 0.
3. PRIMARY profit factor >= 1.10.
4. At least 7 positive calendar years among 2015-2024 with event trades.
5. PRIMARY median net event return >= 0.
6. STRESS mean net return > 0.
7. STRESS profit factor >= 1.03.
8. Remove the best 5% of events by PRIMARY net return: remaining mean >= 0.

### ES current viability — all required
9. >= 10 executed events.
10. PRIMARY mean net ES points/trade > 0.
11. PRIMARY profit factor >= 1.15.
12. At least 2 positive calendar months among Feb/Mar/Apr 2026 with event trades.
13. STRESS mean net ES points/trade > 0.
14. STRESS profit factor >= 1.05.

Terminal classification:
- If all SPY and ES gates pass: `OPENING_GAP_REVERSAL_V1_PASS_FOR_PROPFIRM_RISK_RESEARCH`.
- If SPY passes but ES sample has fewer than 10 events: `STRUCTURAL_PASS_ES_INCONCLUSIVE`.
- Otherwise: `OPENING_GAP_REVERSAL_V1_NO_GO`.

Diagnostics allowed but not rescue filters: gap-up vs gap-down, event gap magnitude, month, year, win/loss distribution. No threshold, direction, weekday, holding-period, stop, or target changes after outcomes are opened.
