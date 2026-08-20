# QQQ ORB Post-Publication Protocol V1

Status before outcome: `FROZEN_BEFORE_POSTPUBLICATION_READ`

## Research question
Does the exact published 5-minute QQQ opening-range momentum rule remain economically positive after the original 2023 publication, under conservative execution costs, strongly enough to justify later prop-firm mapping to NAS100/US100?

## Rule — no parameter optimization
- Instrument for validation: QQQ.
- Timeframe: 5-minute regular-session OHLCV.
- Session: 09:30–16:00 America/New_York.
- Opening bar: 09:30–09:35.
- Bullish opening bar (`close > open`): enter LONG at the 09:35 bar open.
- Bearish opening bar (`close < open`): enter SHORT at the 09:35 bar open.
- Exact doji: skip.
- Stop: opposite extreme of the 09:30 opening bar.
- Profit target: 10R from executed entry, where 1R is entry-to-stop distance after adverse entry slippage.
- Time exit: 15:55 bar close if neither stop nor target was reached.
- No trailing stop, breakeven, VWAP, EMA, gap, weekday, news, volume or volatility filter.
- Maximum one trade per trading day.

## Execution
Primary cost scenario:
- adverse slippage: 1 bp on entry and exit;
- commission: USD 0.005/share per side.

Stress cost scenario:
- adverse slippage: 2 bp on entry and exit;
- commission: USD 0.01/share per side.

Stops and targets use 5-minute OHLC conservatively:
- adverse opening gap through stop fills at the worse executable bar open;
- favorable opening gap through target fills at target, no improvement;
- if stop and target are both touched in one bar, stop wins;
- target fills at target, stop fills at stop unless an adverse gap applies.

## Data
Primary post-publication source: public QQQ 5-minute file in `lvrusu/QQQ_price_data`, currently named `QQQ5m_Ext_J_23_to_Mar_20a_2026.csv`.

The runner must publish data-format diagnostics and reject ambiguous timestamps or missing regular-session bars rather than infer results silently.

## Evaluation window
Original working paper posting date: 2023-04-24.

Post-publication evaluation starts 2023-04-25 and ends at the last complete session available no later than 2026-03-20 in the selected source.

Temporal subperiods:
- A: 2023-04-25 through 2024-12-31;
- B: 2025-01-01 through source end.

## Metrics
For both primary and stress:
- trade count;
- arithmetic mean net R/trade;
- sum net R;
- profit factor;
- win rate;
- max drawdown in R;
- longest losing streak;
- annual sums and means;
- top-5%-winner concentration and mean after removing top ceil(5%) winners.

## PASS gate before any prop-firm simulation
All must hold in the primary scenario:
1. N >= 400 post-publication trades.
2. mean net R >= +0.10R.
3. PF >= 1.25.
4. subperiod A mean > 0 and PF > 1.05.
5. subperiod B mean > 0 and PF > 1.05.
6. max drawdown <= 15R.
7. after removing top ceil(5%) winning trades, remaining mean net R > 0.

Stress scenario must additionally have:
- mean net R > 0;
- PF >= 1.10.

Terminal statuses:
- pass: `QQQ_ORB_POSTPUBLICATION_V1_PASS_FOR_PROPF_MAPPING`
- fail: `QQQ_ORB_POSTPUBLICATION_V1_NO_GO`
- integrity/data failure: `QQQ_ORB_POSTPUBLICATION_V1_INVALID_DATA_ABORT`

No rescue after reading the post-publication outcome. In particular, no change to RR, opening-range duration, side, weekday, gap, volume, volatility, stop, target, exit time, cost model or subperiod exclusion may be used to relabel this V1 as successful.
