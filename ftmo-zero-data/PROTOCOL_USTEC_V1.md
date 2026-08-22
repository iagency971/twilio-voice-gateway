# FTMO Zero-Data USTEC Research V1

Status: `PRE_2025_OOS_FROZEN`

## Hard operational constraint

A candidate is eligible only if live operation can use the native FTMO/MT5 feed for `US100.cash` (or an equivalent FTMO Nasdaq CFD symbol) with **zero paid external market-data subscription**. Any dependence on CME, Databento, footprint/order-flow, paid news, options, or proprietary external feeds is disqualifying.

## Purpose

Test whether a simple, auditable intraday Nasdaq CFD rule family has enough edge to justify a later FTMO-native Free Trial / demo validation.

This stage is deliberately simple. It is not allowed to use 2025 outcomes for parameter selection.

## Public development data

Source repository: `CodyOutcast/Academic-Paper-Data-Source`.

Files used in this stage only:
- `OHLC-USTEC-M1-2021.csv`
- `OHLC-USTEC-M1-2022.csv`
- `OHLC-USTEC-M1-2023.csv`
- `OHLC-USTEC-M1-2024.csv`

The repository identifies the OHLC source as IC Markets. Data columns are `time;open;high;low;close;volume;spread`.

The 2025 file exists but **MUST NOT be downloaded or opened in V1 DEV/validation**.

## Time convention

IC Markets MetaTrader server time is GMT+2 in US standard time and GMT+3 during US daylight saving time, specifically to preserve New-York-close chart alignment. Because the server changes on the US DST schedule, 09:30 America/New_York maps to 16:30 server time in both regimes.

US cash-open anchor used here: `16:30` server time.

## Partitions

- DEV: 2021-01-01 through 2023-12-31.
- VALIDATION: 2024-01-01 through 2024-12-31.
- FINAL OOS: calendar 2025, sealed until a candidate passes the 2024 validation gate and is frozen in a separate manifest.

## Execution assumptions

The source is a CFD proxy, not FTMO. Therefore a pass here is never `LIVE_READY`.

- M1 OHLC is treated as bid-side chart data.
- The file's observed spread is charged in the simulated round trip.
- Entry is always on the next M1 bar after a completed signal bar; no signal-bar-close fill.
- One position maximum at a time and at most one trade per day per candidate.
- Ambiguous same-bar stop/target: stop is assumed first.
- No overnight positions; time exit by 22:55 server time (~15:55 New York).
- PRIMARY uses observed spread and no extra commission (index-CFD style screen).
- STRESS widens observed spread by 50% with a minimum +1.0 index point and adds 0.5 index point adverse slippage per side.

The later FTMO-native test must replace these proxy execution assumptions with observed `US100.cash` bid/ask and actual FTMO execution behavior.

## Candidate families

Only two simple families are screened. No indicators, ML, order flow, volume profile, external news, or futures data are used.

### Family A — Opening Range Breakout continuation

- Opening range: first 15 or 30 minutes from 16:30 server time.
- First M1 close outside the range plus the configured breakout buffer is the signal.
- Entry: next M1 open.
- Structural stop: opposite side of the opening range.
- Target: fixed R multiple.
- Signal cutoff: 19:30 server time (~12:30 New York).

### Family B — Failed Opening Range breakout reversal

- Same opening-range definition.
- A close outside the range plus buffer establishes an attempted breakout.
- If price closes back inside the opening range within 5 M1 bars, enter the opposite direction on the next M1 open.
- Stop: extreme of the failed breakout excursion.
- Target: fixed R multiple.
- Signal cutoff: 19:30 server time.

## Predeclared DEV grid

For each family only:
- opening range: `{15, 30}` minutes;
- target: `{1.0R, 1.5R}`;
- breakout buffer: `{0%, 5%}` of opening-range width.

Eight candidates per family; sixteen total. No other parameter search is allowed in V1.

## DEV screen (2021–2023)

A candidate is DEV-eligible only if all hold in PRIMARY unless stated otherwise:
- `N >= 180`;
- mean >= `+0.05R/trade`;
- PF >= `1.15`;
- closed-trade max drawdown <= `15R`;
- at least 2 of 3 calendar years have positive total R;
- worst calendar-year mean >= `-0.05R/trade`;
- after removing the best 10% of trades, remaining mean >= `0R`;
- STRESS mean > `0R`;
- STRESS PF >= `1.05`.

If no candidate in a family passes, that family is rejected without validation rescue.

If multiple candidates pass, select exactly one per family using only DEV data, maximizing a deterministic robustness score based on worst-year mean, overall mean, sample size, and max drawdown. The exact score is coded before execution.

## 2024 validation gate

For each DEV-selected family winner, all must pass:
- `N >= 50`;
- PRIMARY mean >= `+0.05R/trade`;
- PRIMARY PF >= `1.15`;
- PRIMARY max drawdown <= `10R`;
- after removing best 10%, remaining mean >= `0R`;
- STRESS mean > `0R`;
- STRESS PF >= `1.05`;
- first-half 2024 total R > `0`;
- second-half 2024 total R > `0`;
- at least 55% of active months have positive total R.

A passing family receives `VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS`.

A failing family receives `VALIDATION_NO_GO`. No parameter rescue is permitted after 2024 results are opened.

## 2025 rule

V1 DEV/validation code must not request the 2025 CSV at all.

Only after a 2024 PASS may a separate immutable freeze manifest be written and a one-time 2025 OOS run be authorized.

## Final operational gate after any 2025 OOS pass

Even a 2025 pass remains only `PROXY_RESEARCH_PASS`. Before any paid FTMO account use, the unchanged rules must be tested on FTMO Free Trial/demo using native `US100.cash` prices/spreads. Live operation must require no paid external market data.
