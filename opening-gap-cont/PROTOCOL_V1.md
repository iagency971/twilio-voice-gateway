# ES/SPY Opening-Gap Continuation Scalp V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/es-opening-gap-continuation-v1`

## External hypothesis
Grant, Wolf & Yu (Journal of Banking & Finance, 2005) report that after large S&P 500 futures opening price changes (absolute opening gap >= 0.20%), price initially continues in the direction of the gap for roughly 10 minutes before the later reversal phase.

The separate 60-minute reversal translation has already failed. V1 tests the distinct published INITIAL-CONTINUATION effect; it is not a parameter rescue of the reversal trade.

## Frozen event
- Opening gap = current 09:30 RTH open / previous complete RTH close - 1.
- Event if |gap| >= 0.20%.
- Gap up -> LONG; gap down -> SHORT.
- Both signs included; no weekday/month/volatility filter.

## SPY post-publication test
Data: public `BrianWeiss1/StockList/5min_data_SPY_2015_to_2024.csv`.
Because only 5-minute bars are available and the gap is first known at the 09:30 open, use a conservative causal implementation:
- Observe gap at 09:30.
- Entry = 09:35 bar open, after the first 5 minutes have elapsed.
- Exit = 09:40 bar open.
Thus the trade captures only minutes 5-10 of the published initial-continuation window; no fill at the same opening print that defines the signal.
- PRIMARY cost = 2 bps round-turn.
- STRESS cost = 5 bps round-turn.
Evaluation: all event days 2015-2024.

## Direct ES 2026 test
Data: `axb0306/cme-futures-ohlc`, `ES/ES_1min_20260120_20260415.csv`.
- Gap known from 09:30 open versus prior 15:59 RTH close.
- Entry = 09:31 open (one full minute after signal observability).
- Exit = 09:40 open.
- 1 ES contract, $50/point.
- PRIMARY friction = $30 round-turn.
- STRESS friction = $55 round-turn.

## Predeclared gates
SPY all required:
1. >=150 event trades.
2. PRIMARY mean net return > 0.
3. PRIMARY PF >=1.10.
4. >=7 positive calendar years among 2015-2024.
5. PRIMARY median net return >=0.
6. STRESS mean >0 and PF >=1.03.
7. Remove best 5% of events: remaining mean >=0.

ES current-support gates:
8. >=10 event trades; if fewer, ES is inconclusive rather than automatic failure.
9. If >=10: PRIMARY mean points >0 and PF>=1.15.
10. If >=10: STRESS mean points >0 and PF>=1.05.

Terminal:
- SPY passes and ES passes -> `PASS_FOR_PROPFIRM_RISK_RESEARCH`.
- SPY passes and ES N<10 -> `STRUCTURAL_PASS_ES_INCONCLUSIVE`.
- Otherwise -> `NO_GO`.

No change to gap threshold, direction, entry/exit times, or event subset after outcomes.