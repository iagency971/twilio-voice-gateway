# FOMC SEP Relief Rally V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/fomc-sep-relief-rally-v1`

## External hypothesis
Published evidence: FOMC meetings with a Summary of Economic Projections (SEP) and press conference historically produced a positive equity relief rally in the first hour after the statement. A published trading rule buys E-mini S&P 500 futures 5 minutes before the 14:00 ET announcement and exits 55 minutes after the announcement.

This project does not invent a direction filter, stop, gamma filter, surprise filter, or press-conference text filter.

## Official SEP calendar
SEP meetings are the March, June, September, and December meetings; official Federal Reserve calendars identify SEP meetings with an asterisk.

Frozen post-publication event dates used for SPY 5m replication:
- 2020-06-10, 2020-09-16, 2020-12-16 (no March 2020 SEP was submitted)
- 2021-03-17, 2021-06-16, 2021-09-22, 2021-12-15
- 2022-03-16, 2022-06-15, 2022-09-21, 2022-12-14
- 2023-03-22, 2023-06-14, 2023-09-20, 2023-12-13
- 2024-03-20, 2024-06-12, 2024-09-18, 2024-12-18
Total = 19 events.

## SPY replication
Data: public `BrianWeiss1/StockList` file `5min_data_SPY_2015_to_2024.csv`.
- Use only the 19 dates above.
- Interpret/normalize timestamps to America/New_York if timezone information is available; otherwise treat file wall-clock timestamps as ET after session-anchor QA.
- Entry timestamp = 13:55 ET. Use the 5-minute bar OPEN at 13:55 as the price exactly five minutes before the 14:00 statement.
- Exit timestamp = 14:55 ET. Use the 5-minute bar OPEN at 14:55 as the price exactly 55 minutes after the 14:00 statement.
- LONG only.
- No stop and no intra-window path assumptions.
- PRIMARY transaction cost = 2 bps round-turn.
- STRESS transaction cost = 5 bps round-turn.

## Direct ES 2026 spot check
Data: `axb0306/cme-futures-ohlc`, `ES/ES_1min_20260120_20260415.csv`.
Only the 2026-03-18 SEP meeting lies inside this direct ES window.
- Entry = 13:55 ET open.
- Exit = 14:55 ET open.
- 1 ES contract; $50/point.
- PRIMARY cost = $30 round-turn.
- STRESS cost = $55 round-turn.
This single event is descriptive only and cannot validate/reject the strategy by itself.

## Predeclared SPY gates
Because N=19 is small, this is an event-accelerator test, not a standalone strategy-validation test.
All required:
1. >=18 of 19 official events present and executable.
2. PRIMARY mean net event return > +0.10% (10 bps).
3. PRIMARY profit factor >= 1.30.
4. At least 4 of 5 calendar years 2020-2024 have positive aggregate net event return.
5. Median net event return > 0.
6. STRESS mean net event return > 0.
7. STRESS profit factor >= 1.10.
8. Remove best 2 events: remaining mean net event return >= 0 (concentration gate).

If all pass: `FOMC_SEP_RELIEF_RALLY_V1_PASS_EVENT_ACCELERATOR_CANDIDATE`.
Else: `FOMC_SEP_RELIEF_RALLY_V1_NO_GO_OR_INCONCLUSIVE`.

A PASS does not authorize live trading; next stage would be a second post-publication S&P/ES source and prop-firm event-rule compatibility/risk sizing.
No post-outcome rescue filters are allowed on these 19 events.
