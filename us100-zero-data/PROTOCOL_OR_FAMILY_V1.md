# FTMO Zero-Paid-Data US100 Research — OR Family V1

Status: `DEV_PROTOCOL_FROZEN_2025_CLOSED`

## Hard operational constraint

A strategy is ineligible if live operation requires any paid external market-data feed, order book, footprint, options feed, CME subscription, news feed, or proprietary signal service. The final strategy must be computable from the broker/FTMO MT5 feed itself. Historical research may use public/free archives only.

## Public development data

Pinned public source repository:
- `CodyOutcast/Academic-Paper-Data-Source`
- pinned commit: `50052606c16d71850755e6dbdda02d43b4399c2b`
- source stated by repository: IC Markets
- files: `OHLC-USTEC-M1-2021.csv` through `OHLC-USTEC-M1-2025.csv`

Development window: calendar years **2021–2024 only**.

**2025 is sealed OOS. The 2025 file must not be loaded, summarized, searched for outcomes, or used in parameter choice until a single variant has been frozen from DEV.**

IC Markets documents MetaTrader server/chart time as GMT+2, switching to GMT+3 during US daylight saving. Because the switch follows US DST, 09:30 New York maps to 16:30 IC server time throughout the year. The research therefore uses broker-time session anchors directly.

## Input fields and execution model

Expected M1 fields: `time;open;high;low;close;volume;spread`.

Data QA before economics:
1. timestamps parse and are strictly unique after sorting;
2. zero OHLC consistency violations;
3. spread is finite and non-negative;
4. at least 200 distinct candidate New-York sessions per full calendar DEV year;
5. no silent forward-fill of missing minutes.

The OHLC series is treated as the broker quote-side candle supplied by the archive. To avoid a friction-free backtest, the recorded spread is charged explicitly on both directions via executable prices:
- long entry = next-bar open + spread; long stop/target/market exit evaluated on quote OHLC and exit at quote price;
- short entry = next-bar open; short stop/target/market exit is evaluated with ask-equivalent OHLC = quote OHLC + spread and exit price includes spread.

This is deliberately conservative and will later be replaced by direct FTMO `US100.cash` bid/ask logging if a candidate survives.

No commission is added in this research family because the intended FTMO index product is commission-free; spread remains the primary friction. A separate stress scenario doubles every recorded spread.

No look-ahead: signals are generated only from a fully closed M1 bar; fills occur at the next M1 open.

Same-bar stop/target ambiguity is resolved adversely: if both could be hit within the same M1 bar, stop is assumed first.

Maximum one trade per broker day. No averaging, martingale, grid, recovery sizing, or overlapping positions.

## Family V1 — New York opening-range price action

Only the following variants may be evaluated on DEV. No other filter or parameter may be introduced after DEV outcomes are opened.

### A. ORB continuation

Opening range length `L` in `{15, 30}` minutes beginning at 16:30 broker time.

After the opening range is complete and before 19:00 broker time:
- LONG signal: a closed M1 candle closes strictly above opening-range high;
- SHORT signal: a closed M1 candle closes strictly below opening-range low.

First valid signal of the day only. Entry next M1 open. Initial stop is the opposite opening-range edge. Target is fixed `RR` in `{1.0, 1.5, 2.0}` measured from executable entry to stop. Any open position is closed at the 22:55 broker-time bar close.

### B. ORF failure/reversal

Opening range length `L` in `{15, 30}` minutes beginning at 16:30 broker time.

After the range is complete and before 19:00 broker time:
- SHORT signal: a closed M1 bar trades above OR high (`high > ORH`) but closes back strictly below OR high;
- LONG signal: a closed M1 bar trades below OR low (`low < ORL`) but closes back strictly above OR low.

First valid signal of the day only. Entry next M1 open. Stop is the signal bar excursion extreme (high for short, low for long), rejected if executable risk is <= 0. Target uses `RR` in `{1.0, 1.5, 2.0}`. Any open position is closed at 22:55.

No wick-size threshold, EMA filter, ATR filter, day-of-week filter, volatility filter, news filter, direction filter, or range-width filter is permitted in V1.

Total predeclared DEV variants: 2 families × 2 range lengths × 3 RRs = **12 variants**.

## DEV selection gate — 2021–2024

Statistics use R-multiples after recorded spread. Each variant is reported overall and separately for 2021, 2022, 2023, 2024.

A variant is eligible for OOS only if all are true in PRIMARY recorded-spread DEV:
- `N >= 400` total trades;
- frequency `>= 0.45 trade / candidate session`;
- overall expectancy `>= +0.05R/trade`;
- overall PF `>= 1.15`;
- closed-trade max drawdown `<= 15R`;
- at least 3 of 4 calendar years have positive total R;
- doubled-spread STRESS expectancy remains `> 0` and PF `>= 1.05`.

If multiple variants pass, select exactly one using this deterministic hierarchy:
1. highest **median calendar-year expectancy**;
2. tie: lower max drawdown;
3. tie: higher total N.

If no variant passes, status is `OR_FAMILY_V1_DEV_NO_GO`; **2025 remains unopened** and the family is rejected without rescue tuning.

## 2025 OOS gate — only after freeze

Before loading 2025, write `OOS_UNLOCK.json` containing the exact selected family, L, RR, source commit, code SHA/hash, and DEV summary.

The selected variant is then evaluated exactly once on 2025. OOS PASS requires all:
- `N >= 80`;
- frequency `>= 0.40 trade / candidate session`;
- PRIMARY expectancy `>= +0.05R/trade`;
- PRIMARY PF `>= 1.15`;
- PRIMARY max DD `<= 12R`;
- at least 7 of 12 calendar months have positive total R;
- doubled-spread STRESS expectancy `> 0` and PF `>= 1.05`;
- after removing the best 10% of PRIMARY trades, remaining expectancy `>= 0`.

If PASS, status is `OR_FAMILY_V1_OOS_PASS_REQUIRES_FTMO_FEED_PARITY`. It is not LIVE_READY until direct FTMO Free-Trial `US100.cash` bid/ask logging confirms execution parity.

## Prohibited rescue actions

After DEV outcomes are opened: no new RR, no new opening-range length, no time-window adjustment, no model combination, no direction deletion, no day/date exclusion, no stop redesign, and no filter addition inside V1. If V1 fails, a genuinely new family requires a new pre-outcome protocol.