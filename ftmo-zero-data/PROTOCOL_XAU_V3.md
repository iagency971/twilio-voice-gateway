# FTMO Zero-Data XAUUSD Research V3

Status: `PRE_2024_VALIDATION_FROZEN`

USTEC V1/V2 are closed as DEV NO_GO. V3 is a distinct Gold hypothesis family and is not a rescue of the rejected Nasdaq rules.

## Hard operational constraint

A strategy is eligible only if live operation can run from FTMO/MT5 native `XAUUSD` prices with **zero paid external market-data subscription**. CME/COMEX, Databento, footprint/order-flow, paid news, options data, or proprietary external feeds are forbidden dependencies.

## Public development data

Public repository: `tiumbj/M1_XAUUSD`, files named `DAT_MT_XAUUSD_M1_<YEAR>.csv`.

The file format matches HistData MetaTrader M1: date, time, Bid open/high/low/close, volume. HistData documents these timestamps as fixed Eastern Standard Time (UTC-5) **without daylight-saving adjustment**. The runner therefore localizes source timestamps to fixed UTC-5 and converts them to `America/New_York` before any session logic.

Partitions:
- DEV: 2021-01-01 through 2023-12-31.
- VALIDATION: calendar 2024.
- FINAL OOS: calendar 2025, sealed. V3 code must refuse any year >=2025.

2024 data may be opened for structural QA, but no 2024 strategy outcomes may be computed unless a DEV candidate passes its frozen gates.

## FTMO-like transaction-cost screen

The public M1 bars are Bid OHLC and contain no Ask series. Therefore execution costs are imposed explicitly.

PRIMARY:
- fixed Gold spread: `$0.30`;
- Metals CFD commission: `0.0007% of notional per side`;
- no additional slippage.

STRESS:
- fixed Gold spread: `$0.50`;
- same `0.0007% of notional per side` commission;
- `$0.05` adverse price slippage per side.

For XAUUSD with a standard 100-ounce lot, the commission's equivalent price cost per side is `price × 0.000007`. R results include spread, commission and scenario slippage before normalization by initial risk.

These are research-screen assumptions only. Any passing strategy must later be validated unchanged on an FTMO Free Trial/demo with directly observed native `XAUUSD` Bid/Ask and actual commissions/execution.

## Common execution rules

- M1 source resampled causally to M5.
- H1 trend state uses only completed H1 bars.
- Signal window: `08:20–12:00 America/New_York`.
- Entry: next M5 bar open after a completed signal bar.
- No signal-bar-close fill.
- Maximum 3 entries per New York date.
- Minimum 30 minutes between entries.
- No overlapping trades.
- Same-bar stop and target ambiguity: stop first.
- Force flat at `15:55 America/New_York`.
- No overnight positions.

## Family A — `PB_LONG`

Long-only trend pullback/reclaim, a mechanical proxy for buying Gold retracements in an established uptrend.

Signal on completed M5 bar:
- latest completed H1 EMA20 > H1 EMA50;
- H1 EMA50 > its value 3 completed H1 bars earlier;
- previous M5 close <= previous M5 EMA20;
- current M5 close > current M5 EMA20.

Stop distance from next-bar Bid open: configured multiple of M5 ATR14.
Target: configured fixed R multiple.

## Family B — `PB_BI`

Same long rule as `PB_LONG`, plus symmetric shorts when H1 EMA20 < EMA50, H1 EMA50 is falling, and M5 reclaims below EMA20 after a pullback above it.

## Previous-session levels

For sweep families, a Gold trading session is defined as `17:00 New York` through `16:59` the following day. Previous-session high/low are computed from the immediately preceding available session and are fixed before the current session begins.

## Family C — `SWEEP_LONG`

Long-only liquidity-rejection proxy:
- current M5 low trades below the previous session low by at least the configured fraction of M5 ATR14;
- the completed M5 bar closes back above the previous session low.

Stop: current signal-bar low minus `0.10 × ATR14`.
Target: configured fixed R multiple.

A previous-session-low long may be attempted at most once per New-York date.

## Family D — `SWEEP_BI`

Same PDL long rule as `SWEEP_LONG`, plus symmetric short rejection of the previous-session high.

A PDL long and a PDH short may each be attempted at most once per New-York date.

## Predeclared DEV grid

Pullback families, each 4 candidates:
- stop `{1.5, 2.0} × ATR14`;
- target `{1.5R, 2.0R}`.

Sweep families, each 4 candidates:
- minimum penetration `{0.00, 0.10} × ATR14`;
- target `{1.5R, 2.0R}`.

Total: exactly 16 candidates across four families. No additional parameter search in V3.

## Speed metric

`R/session = total PRIMARY R / available New-York morning sessions`.

This is deliberately part of the gate: a statistically positive system that is too slow to be operationally useful for a prop challenge is rejected.

## DEV gate — 2021–2023

A candidate is DEV-eligible only if all hold:
- N >= 250 trades;
- PRIMARY mean >= `+0.15R/trade`;
- PRIMARY PF >= `1.30`;
- PRIMARY `R/session >= +0.35R`;
- PRIMARY closed-trade max DD <= `12R`;
- at least 2 of 3 calendar years have positive total R;
- worst calendar-year mean >= `0R/trade`;
- at least 58% of active months have positive total R;
- STRESS mean > `0R/trade`;
- STRESS PF >= `1.15`;
- STRESS `R/session >= +0.15R`;
- 5th percentile of deterministic 5,000-replication contiguous 20-trade block-bootstrap mean >= `0R`.

Bootstrap seed: `260822`.

If no candidate in a family passes, that family is rejected and receives no 2024 economic evaluation.

If multiple candidates pass within a family, select exactly one from DEV only using a frozen robustness score emphasizing worst-year mean, stress R/session, PRIMARY R/session, and lower max DD.

## 2024 validation gate

For each DEV-selected family winner, all must hold:
- N >= 70 trades;
- PRIMARY mean >= `+0.15R/trade`;
- PRIMARY PF >= `1.30`;
- PRIMARY `R/session >= +0.40R`;
- PRIMARY max DD <= `10R`;
- STRESS mean > `0R/trade`;
- STRESS PF >= `1.15`;
- STRESS `R/session >= +0.18R`;
- first-half 2024 total R > 0;
- second-half 2024 total R > 0;
- at least 58% of active months positive;
- bootstrap 5th-percentile mean >= `0R`.

Pass status: `VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS`.
Failure: `VALIDATION_NO_GO`. No post-2024 parameter rescue is permitted.

## 2025 and FTMO-native rule

V3 DEV/validation code must not request, download or open the 2025 file.

Only a 2024 PASS may be frozen in a separate immutable manifest before a one-time 2025 OOS run.

Even a 2025 OOS pass is only `PROXY_RESEARCH_PASS`. Before any paid FTMO account use, the unchanged strategy must pass a prospective FTMO Free Trial/demo using native `XAUUSD`, observed Bid/Ask, commissions, slippage, and drawdown. Live operation must require **0 EUR/month of external market data**.
