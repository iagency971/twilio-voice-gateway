# FTMO Zero-Data USTEC Trend-Pullback V2

Status: `PRE_2024_VALIDATION_FROZEN`

V1 ORB is closed/rejected. V2 is a distinct higher-frequency hypothesis family and does not rescue V1 parameters.

## Hard operational constraint

Live operation must require only FTMO/MT5 native `US100.cash` price/spread data. Paid CME, Databento, order flow, footprint, options, paid news, or any external paid market-data feed is forbidden.

## Data partitions

Public proxy source: `CodyOutcast/Academic-Paper-Data-Source`, OHLC source identified by that repository as IC Markets USTEC M1.

- DEV: 2021–2023.
- VALIDATION: 2024.
- FINAL OOS: 2025 sealed. V2 code must refuse to request 2025+.

IC Markets server alignment maps the New York cash open 09:30 to 16:30 server time throughout the year.

## Rationale

The rejected V1 ORB family produced approximately one trade/day and too little robust edge for the user's prop-challenge objective. V2 therefore tests a more frequent but still mechanically simple trend-pullback/reclaim pattern.

## Bars and features

- Source M1 is resampled to M5 OHLC.
- Spread for each M5 bar is the last observed M1 spread in that bar.
- EMA20 and EMA50 are calculated causally on M5 closes.
- ATR14 uses standard true range and is calculated causally.
- Trading window: 16:30 through 22:30 server time (~09:30–15:30 New York).
- All positions forced flat by 22:55 server time.

## Signal

Long candidate when, on a completed M5 bar:
- EMA20 > EMA50;
- EMA50 is rising versus 3 M5 bars earlier;
- `(EMA20 - EMA50) / ATR14` is at least the configured trend-strength threshold;
- previous close <= previous EMA20;
- current close > current EMA20.

Short is symmetric.

Entry is next M5 bar open. No signal-bar fill.

## Exit and execution

- Stop distance: configured multiple of ATR14 at the signal bar.
- Target: fixed configured R multiple.
- Maximum 3 completed entries/day.
- Minimum 30 minutes between entries.
- No overlapping positions.
- Same-bar stop/target ambiguity is resolved against the strategy: stop first.
- PRIMARY charges the observed CFD spread.
- STRESS uses `max(1.5 × observed spread, observed spread + 1 index point)` and 0.5 index point adverse slippage per side.
- No commission is assumed for the index-CFD screen; FTMO-native validation must replace proxy costs with observed `US100.cash` bid/ask/execution.

## Predeclared DEV grid

Exactly 8 variants:
- trend-strength threshold: `{0.00, 0.10}` ATR;
- stop: `{1.0, 1.5}` ATR;
- target: `{1.5R, 2.0R}`.

No other parameter search in V2.

## DEV eligibility 2021–2023

All required:
- N >= 900 trades;
- >= 1.5 trades per available US-open session;
- PRIMARY mean >= +0.10R/trade;
- PRIMARY PF >= 1.25;
- PRIMARY max closed-trade drawdown <= 15R;
- at least 2/3 calendar years positive;
- worst calendar-year mean >= 0R/trade;
- at least 55% active months positive;
- STRESS mean > 0R;
- STRESS PF >= 1.10;
- deterministic block-bootstrap 5th percentile of mean R >= 0R.

The bootstrap samples contiguous 20-trade blocks, 5,000 replications, with seed 260822.

If no variant passes, V2 is `DEV_NO_GO` and 2024 strategy outcomes are not opened.

If variants pass, choose exactly one using DEV only by maximizing a frozen robustness score weighted toward worst-year mean, stress mean, overall mean, and lower drawdown.

## 2024 validation gate

For the single DEV-selected variant, all required:
- N >= 300;
- >= 1.5 trades per available US-open session;
- PRIMARY mean >= +0.12R/trade;
- PRIMARY PF >= 1.25;
- PRIMARY max DD <= 12R;
- STRESS mean >= +0.05R/trade;
- STRESS PF >= 1.15;
- H1 total R > 0 and H2 total R > 0;
- >= 58% active months positive;
- bootstrap 5th-percentile mean >= 0R.

Pass status: `VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS`.
Failure: `VALIDATION_NO_GO`; no parameter rescue.

## 2025 and FTMO rule

2025 remains sealed until a 2024 pass is frozen separately. Even a later 2025 pass is only proxy evidence. Final deployment requires an unchanged FTMO Free Trial/demo run using native `US100.cash`, with no paid data subscription.
