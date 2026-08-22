# FTMO Zero-Paid-Data US100 Research — VWAP Rejection V2

Status: `V2_DEV_PROTOCOL_FROZEN_2024_OUTCOMES_CLOSED`

## Operational hard gate

Live operation must require **zero paid external market data**. Signals and execution must be computable from native FTMO/MT5 US100.cash M1 OHLC, tick volume and bid/ask/spread only. No CME, order book, footprint, options, paid news, or proprietary signal feed is allowed.

## Historical source

Pinned public archive:
- repository: `CodyOutcast/Academic-Paper-Data-Source`
- commit: `50052606c16d71850755e6dbdda02d43b4399c2b`
- stated source: IC Markets USTEC M1

Spread semantics remain frozen from V1.1: MetaTrader spread is in symbol points; USTEC is quoted to one decimal place; `spread_price = recorded_spread * 0.1`.

V2 development years: **2021, 2022, 2023**.

V2 OOS year: **2024**, whose V2 outcomes must not be calculated until one V2 variant is frozen from 2021–2023.

Note: aggregate 2024 results of the unrelated OR-family V1 were previously observed. Therefore 2024 is family-specific outcome holdout, not globally pristine market-regime OOS. Any V2 historical PASS still requires prospective FTMO Free-Trial validation before operational use.

## Session and features

Broker/IC server time is used. New York 09:30 maps to broker 16:30 throughout the year because IC changes GMT offset with US DST.

For each broker day, start the research session at 16:30.

From M1 bars compute causally:
- typical price = `(high + low + close) / 3`;
- session VWAP = cumulative `typical_price * volume / cumulative volume` from 16:30 through the current closed bar;
- ATR14 = rolling 14-bar true range within the same session, using prior M1 close.

No future bars or end-of-day statistics may enter a signal.

## Family V2 — VWAP/ATR rejection fade

Threshold multiplier `K` in `{1.0, 1.5, 2.0}`.

Fixed target RR in `{1.0, 1.5, 2.0}`.

Total predeclared variants: **9**.

Signal window: 17:00 inclusive to 20:30 exclusive broker time.

On each fully closed M1 bar:
- lower band = `VWAP - K * ATR14`;
- upper band = `VWAP + K * ATR14`;
- LONG rejection signal if `low < lower_band` and `close > lower_band`;
- SHORT rejection signal if `high > upper_band` and `close < upper_band`.

First valid signal of the day only.

Entry is next M1 open using executable spread mapping:
- long entry = bid open + spread_price;
- short entry = bid open.

Stop:
- long = signal-bar low;
- short = signal-bar high; short trade rejected if next-bar ask is already at/above the stop.

Target = fixed RR times executable entry-to-stop risk.

Same-bar stop/target ambiguity is resolved adversely (stop first). Any open trade is closed at 22:55 broker time. Maximum one trade/day. No averaging, martingale, grid, recovery sizing, direction filter, weekday filter, news filter, EMA filter, volatility-regime filter, or manual exclusion.

PRIMARY uses recorded spread. STRESS doubles the converted recorded spread on every bar.

## DEV gate — 2021–2023

For each of the 9 variants report overall and calendar-year statistics.

A variant is V2 DEV-eligible only if all are true in PRIMARY:
- N >= 250;
- frequency >= 0.35 trade / candidate session;
- expectancy >= +0.05R/trade;
- PF >= 1.15;
- max closed-trade DD <= 15R;
- **all 3 calendar years positive**;
- STRESS expectancy > 0;
- STRESS PF >= 1.05.

If multiple variants pass, select exactly one by:
1. highest median calendar-year expectancy;
2. tie: lower max DD;
3. tie: higher N.

If none pass: `VWAP_REJECTION_V2_DEV_NO_GO`; 2024 V2 outcomes remain unopened.

## 2024 OOS gate

Before calculating 2024, write a V2 OOS lock containing exact K, RR, source commit, code hash and DEV summary.

PASS requires all:
- N >= 60;
- frequency >= 0.30 trade / candidate session;
- PRIMARY expectancy >= +0.05R/trade;
- PRIMARY PF >= 1.15;
- PRIMARY max DD <= 12R;
- at least 3 of 4 calendar quarters positive;
- STRESS expectancy > 0 and PF >= 1.05;
- **leave-one-quarter-out robustness:** for each Q1–Q4, removing that quarter leaves the remaining three quarters with total PRIMARY R > 0.

If all pass: `VWAP_REJECTION_V2_2024_OOS_PASS_REQUIRES_FTMO_FORWARD`. Otherwise `VWAP_REJECTION_V2_2024_OOS_NO_GO`.

No rescue tuning is permitted after DEV outcomes open. A failed V2 requires a new family/protocol.