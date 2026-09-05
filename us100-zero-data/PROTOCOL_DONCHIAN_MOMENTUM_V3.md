# FTMO Zero-Paid-Data US100 Research — Donchian Momentum V3

Status: `V3_DEV_PROTOCOL_FROZEN_2024_AND_2025_OUTCOMES_CLOSED`

## Hard operational constraint

The strategy is ineligible if live operation requires any paid external market-data subscription. All signals, stops, sizing inputs and exits must be computable from native FTMO/MT5 `US100.cash` M1 OHLC and bid/ask/spread only. No CME, order book, footprint, options, paid news, or proprietary signal feed is permitted.

Historical research uses only the pinned free public IC Markets USTEC M1 archive:
- repository: `CodyOutcast/Academic-Paper-Data-Source`
- commit: `50052606c16d71850755e6dbdda02d43b4399c2b`
- spread conversion frozen from V1.1: `spread_price = recorded_spread * 0.1`.

## Validation ladder

- DEV: 2021, 2022, 2023.
- Stage-1 OOS: full calendar 2024, family-specific outcomes unopened before V3 selection.
- Stage-2 confirmation: available 2025 coverage 2025-01-02 through 2025-04-30, only if 2024 passes, with **zero parameter change after 2024**.
- Any historical PASS still requires prospective FTMO Free-Trial validation because previous research has exposed general market behavior in these calendar periods.

## Broker-time session

IC/MetaTrader broker time is used. New York 09:30 maps to 16:30 broker time through the year.

Research session starts at 16:30 broker time.
Signal window: 17:00 inclusive through 20:30 exclusive.
Hard flatten: 22:55 broker time.

A candidate day requires:
- all 30 bars 16:30–16:59 present contiguously;
- at least 120 M1 bars present in 17:00–20:29;
- no missing minute is forward-filled.

## Causal features

Within each broker day from 16:30 onward:
- ATR14 = simple rolling mean of 14 one-minute true ranges, using only closed bars;
- Donchian lookback uses the previous `N` fully closed bars **within the same session**, excluding the current signal bar.

Lookback `N` in `{20, 40, 60}`.
ATR stop multiplier `M` in `{1.0, 1.5}`.
Fixed target RR in `{1.5, 2.0}`.

Total predeclared variants: **12**.

## Signal

For each fully closed M1 bar inside the signal window, once at least N prior session bars exist:
- prior_high = maximum high of previous N bars, excluding current bar;
- prior_low = minimum low of previous N bars, excluding current bar;
- LONG signal if current close is strictly above prior_high;
- SHORT signal if current close is strictly below prior_low.

First valid signal of the day only.

No EMA filter, VWAP filter, opening-range filter, direction filter, weekday filter, volatility regime filter, news filter, wick filter, volume threshold, or manual exclusion.

## Execution

Signal on closed M1, fill at next M1 open.

PRIMARY uses recorded spread; STRESS doubles converted recorded spread.
- long executable entry = next-bar bid open + spread;
- short executable entry = next-bar bid open.

ATR used for the stop is the ATR14 value known on the closed signal bar.
- long stop = executable entry - `M * ATR14`;
- short stop = executable entry + `M * ATR14`.

Target = fixed RR times initial executable risk.

For short positions, stop/target checks use ask-equivalent OHLC = bid OHLC + current spread. Long checks use bid OHLC. Same-bar stop/target ambiguity is adverse: stop first.

Maximum one trade/day. No averaging, grid, martingale, recovery sizing or overlapping positions. Flatten remaining position at 22:55.

## DEV gates — 2021–2023

A variant is eligible only if all PRIMARY/robustness gates pass:
- N >= 250;
- frequency >= 0.30 trade/candidate session;
- overall expectancy >= +0.08R/trade;
- PF >= 1.20;
- closed-trade max DD <= 15R;
- all 3 calendar years positive;
- STRESS expectancy >= +0.03R/trade;
- STRESS PF >= 1.10.

If several pass, select exactly one by:
1. highest median calendar-year PRIMARY expectancy;
2. tie: lower PRIMARY max DD;
3. tie: higher N.

If none pass: `DONCHIAN_MOMENTUM_V3_DEV_NO_GO`; 2024 V3 outcomes remain unopened.

## Stage-1 OOS gates — 2024

Before opening V3 2024 economics, write an OOS lock containing exact N/M/RR, source commit, code hash and DEV summary.

PASS requires all:
- N >= 70;
- frequency >= 0.28;
- PRIMARY expectancy >= +0.05R/trade;
- PRIMARY PF >= 1.15;
- PRIMARY max DD <= 12R;
- at least 3 of 4 quarters positive;
- STRESS expectancy > 0 and PF >= 1.05;
- leave-one-quarter-out robustness: removing each quarter in turn leaves the remaining three quarters with total PRIMARY R > 0.

If fail: `DONCHIAN_MOMENTUM_V3_2024_OOS_NO_GO`, stop. No 2025 V3 economics.

## Stage-2 gates — Jan-Apr 2025, only after 2024 PASS

No parameter change is permitted between 2024 and 2025.

PASS requires all:
- N >= 20;
- frequency >= 0.25;
- PRIMARY expectancy >= +0.03R/trade;
- PRIMARY PF >= 1.10;
- PRIMARY max DD <= 8R;
- at least 3 of 4 months positive;
- STRESS expectancy > 0 and PF >= 1.03;
- leave-one-month-out robustness: removing each month in turn leaves the other three months with total PRIMARY R > 0.

Historical success status: `DONCHIAN_MOMENTUM_V3_HISTORICAL_PASS_REQUIRES_FTMO_FORWARD`.

No rescue tuning is permitted after DEV outcomes open. A failure at any stage rejects V3.