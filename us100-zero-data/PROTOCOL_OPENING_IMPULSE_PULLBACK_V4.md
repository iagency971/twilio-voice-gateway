# FTMO Zero-Paid-Data US100 Research — Opening Impulse Pullback V4

Status: `V4_DEV_PROTOCOL_FROZEN_2024_AND_2025_OUTCOMES_CLOSED`

## Operational hard gate

Live operation must require zero paid external market data. Everything must be computable from native FTMO/MT5 `US100.cash` M1 OHLC, tick volume and bid/ask/spread. Historical research uses the pinned free IC Markets USTEC M1 archive only.

Pinned archive:
- `CodyOutcast/Academic-Paper-Data-Source`
- commit `50052606c16d71850755e6dbdda02d43b4399c2b`
- spread conversion: `spread_price = recorded_spread * 0.1`.

## Validation ladder

- DEV: 2021–2023.
- Stage-1 family-specific OOS: 2024, unopened for V4 until one variant is frozen.
- Stage-2 family-specific confirmation: available 2025-01-02 through 2025-04-30, only after 2024 PASS, with no parameter change.
- Historical PASS still requires prospective FTMO Free-Trial validation.

Previous families have exposed general market behavior, so V4 holdouts are family-specific rather than globally pristine.

## Broker-time mapping and session QA

New York 09:30 = broker 16:30.
Opening range (OR): all 30 bars 16:30 through 16:59.
Signal window: 17:00 inclusive through 19:30 exclusive.
Flatten: 22:55.

Candidate session requires:
- all 30 OR bars contiguous;
- at least 120 M1 bars in 17:00–19:29;
- no missing-minute fill.

## Causal features

From 16:30 onward compute session VWAP causally using typical price `(H+L+C)/3` weighted by tick volume.

From the 30-minute opening range compute after 16:59 only:
- OR high, low, open, close;
- OR width = high-low;
- close-location-value `CLV = (OR_close - OR_low) / OR_width` if width>0.

## Opening impulse definition

Impulse threshold `Q` in `{0.67, 0.80}`.

- LONG bias if `CLV >= Q`.
- SHORT bias if `CLV <= 1-Q`.
- otherwise no trade that day.

This uses no future data and no trend/EMA/news/day filter.

## Pullback/reclaim signal

After 17:00 and before 19:30, scan closed M1 bars in time order.

For LONG bias:
- current bar low is at or below current causal session VWAP;
- current bar closes strictly above VWAP.

For SHORT bias:
- current bar high is at or above current causal session VWAP;
- current bar closes strictly below VWAP.

First valid signal only. If no reclaim occurs, no trade.

## Execution

Fill at next M1 open.
PRIMARY uses recorded spread; STRESS doubles it.
- long entry = next-bar bid open + spread;
- short entry = next-bar bid open.

Stop is the signal-bar pullback extreme:
- long stop = signal low;
- short stop = signal high; reject if next-bar ask is already at/above stop.

Target fixed RR in `{1.5, 2.0}` times executable entry-to-stop risk.

Thus total predeclared variants = 2 impulse thresholds × 2 RRs = **4**.

Same-bar stop/target ambiguity: stop first. Short stop/target checks use ask-equivalent OHLC; long uses bid OHLC. Hard flatten at 22:55. Maximum one trade/day. No averaging, grid, martingale, recovery sizing, overlapping positions or parameter adaptation.

## DEV gates — 2021–2023

Variant passes DEV only if all:
- N >= 180;
- frequency >= 0.25 trade/candidate session;
- PRIMARY expectancy >= +0.10R/trade;
- PRIMARY PF >= 1.25;
- PRIMARY max DD <= 12R;
- all three calendar years positive;
- STRESS expectancy >= +0.05R/trade;
- STRESS PF >= 1.15.

If several pass, select exactly one by:
1. highest median calendar-year PRIMARY expectancy;
2. lower PRIMARY max DD;
3. higher N.

If none pass: `OPENING_IMPULSE_PULLBACK_V4_DEV_NO_GO`; do not open 2024 V4 economics.

## Stage-1 OOS — 2024

Before opening outcomes, write an exact V4 lock containing Q, RR, source commit, code hash and DEV summary.

PASS requires all:
- N >= 55;
- frequency >= 0.22;
- PRIMARY expectancy >= +0.07R/trade;
- PRIMARY PF >= 1.20;
- PRIMARY max DD <= 10R;
- at least 3 of 4 quarters positive;
- STRESS expectancy >= +0.02R and PF >= 1.08;
- removing each quarter in turn leaves the other three quarters with total PRIMARY R > 0.

Failure stops V4 and leaves 2025 V4 unopened.

## Stage-2 confirmation — Jan-Apr 2025

Only after 2024 PASS, unchanged Q/RR.

PASS requires all:
- N >= 18;
- frequency >= 0.20;
- PRIMARY expectancy >= +0.05R/trade;
- PRIMARY PF >= 1.15;
- PRIMARY max DD <= 7R;
- at least 3 of 4 months positive;
- STRESS expectancy > 0 and PF >= 1.05;
- removing each month in turn leaves the other three months with total PRIMARY R > 0.

Historical success status: `OPENING_IMPULSE_PULLBACK_V4_HISTORICAL_PASS_REQUIRES_FTMO_FORWARD`.

No rescue tuning after DEV outcomes open.