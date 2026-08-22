# FTMO Zero-Data XAUUSD Session-Liquidity V4

Status: `PRE_2024_VALIDATION_FROZEN`

V3 pullback and previous-session-sweep families are closed as DEV NO_GO. V4 is a distinct hypothesis about New-York reactions to Asia/London session ranges; it does not modify or rescue V3.

## Hard operational constraint

Live deployment must use only native FTMO/MT5 `XAUUSD` Bid/Ask. Paid CME/COMEX, Databento, footprint/order-flow, options, paid news or any external paid market-data subscription are forbidden.

## Data and partitions

Same public HistData-format XAUUSD M1 proxy used by V3:
- public repository `tiumbj/M1_XAUUSD`;
- Bid OHLC M1;
- source timestamps fixed EST (UTC-5) without DST; convert to `America/New_York` before session logic.

Partitions:
- DEV: 2021–2023;
- VALIDATION: 2024, gated;
- FINAL OOS: 2025, sealed and forbidden to V4 code.

## Cost model

Same predeclared FTMO-like research screen as V3.

PRIMARY:
- XAUUSD spread `$0.30`;
- Metals CFD commission `0.0007% of notional per side`;
- no added slippage.

STRESS:
- spread `$0.50`;
- same commission;
- `$0.05` adverse slippage per side.

Final FTMO Free Trial/demo must replace these assumptions with observed native Bid/Ask and actual executions.

## Time ranges — America/New_York

All features use completed M5 bars.

For each New-York calendar date D:
- `ASIA` range = 18:00 on D-1 through 01:59 on D;
- `LONDON` range = 02:00 through 08:19 on D;
- trade-signal window = 08:20 through 11:30 on D;
- force flat = 15:55 on D.

A session range is valid only if it contains at least 75% of its nominal M5 bars.

## Family A — `ASIA_SWEEP`

First qualifying rejection of either Asia range edge during the signal window:
- LONG: M5 low penetrates below Asia low by at least configured ATR fraction, then closes back above Asia low;
- SHORT: M5 high penetrates above Asia high by at least configured ATR fraction, then closes back below Asia high.

At most one LONG and one SHORT attempt/day; no overlap; 30-minute entry cooldown.
Stop: signal-bar extreme plus/minus `0.10 × ATR14`.
Target: fixed configured R multiple.

## Family B — `LONDON_SWEEP`

Identical sweep/rejection logic, using the London pre-New-York high/low.

## Family C — `ASIA_BREAK`

First completed M5 close outside the Asia range by at least configured ATR fraction.
Direction follows breakout.
Entry next M5 open.
Stop: `1.0 × ATR14` from next-bar Bid open.
Target: configured R multiple.
At most one breakout trade/day.

## Family D — `LONDON_BREAK`

Identical continuation logic, using the London range.

## Predeclared grid

For each family, exactly 4 candidates:
- penetration/breakout threshold `{0.00, 0.10} × ATR14`;
- target `{1.5R, 2.0R}`.

Total: exactly 16 candidates. No further parameter search in V4.

## DEV gate — 2021–2023

A candidate passes only if all hold:
- N >= 250;
- PRIMARY mean >= `+0.15R/trade`;
- PRIMARY PF >= `1.30`;
- PRIMARY `R/session >= +0.30R`;
- PRIMARY max closed-trade DD <= `12R`;
- at least 2/3 calendar years positive;
- worst calendar-year mean >= `0R/trade`;
- >=58% active months positive;
- STRESS mean > 0;
- STRESS PF >= `1.15`;
- STRESS `R/session >= +0.12R`;
- deterministic 5,000-rep contiguous 20-trade block-bootstrap 5th-percentile mean >= 0.

Bootstrap seed: `260822`.

If a family has multiple passing candidates, select one using DEV only with a frozen score emphasizing worst-year mean, stress R/session, PRIMARY R/session and lower DD.

No DEV pass => that family gets no 2024 economic evaluation.

## 2024 validation gate

For each DEV-selected family winner, all required:
- N >= 70;
- PRIMARY mean >= `+0.15R/trade`;
- PRIMARY PF >= `1.30`;
- PRIMARY `R/session >= +0.35R`;
- PRIMARY max DD <= `10R`;
- STRESS mean > 0;
- STRESS PF >= `1.15`;
- STRESS `R/session >= +0.15R`;
- H1 total R > 0 and H2 total R > 0;
- >=58% active months positive;
- bootstrap p05 mean >= 0.

Pass: `VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS`.
Fail: `VALIDATION_NO_GO`. No post-validation rescue.

## 2025 / FTMO rule

V4 code must refuse any year >=2025. 2025 can only be opened after a separately frozen 2024 PASS manifest.

Even a future 2025 pass remains proxy evidence. Before any paid FTMO account use, the unchanged strategy must run prospectively on FTMO Free Trial/demo using native `XAUUSD` and must require `0 EUR/month` external market-data spend.
