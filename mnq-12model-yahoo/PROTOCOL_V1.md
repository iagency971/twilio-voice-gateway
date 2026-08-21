# MNQ/NQ 12-Model Yahoo Forward Holdout V1

Status before outcomes: `PREOUTCOME_FROZEN_FORWARD`
Branch: `agent/mnq-12model-yahoo-forward-v1`

## Objective
Perform a zero-cost, genuinely post-freeze forward sanity test of the externally published 12-model MNQ/NQ ensemble using recent Yahoo Finance E-mini Nasdaq-100 futures (`NQ=F`) 1-minute bars.

This is stronger than the Jun-Jul GetData proxy screen because the economic evaluation period is August 2026, which has not been used to modify the external system or our frozen ensemble rules. It is still not a substitute for licensed CME historical validation.

## External strategy freeze
Repository: `s-k-28/nq-es-trader-5k-payout`.
Pinned code: `d472d6b442764c2adafbba4bbeb96881c100e3e0` (2026-05-31).
No model, parameter, quality threshold, conflict rule, stop/target, BE rule, time stop, or daily cap is modified.

## Yahoo data
Ticker: `NQ=F`.
Interval: 1 minute.
Download recent history in small chunks via `yfinance`, `auto_adjust=False`, `prepost=True`.
Convert timezone-aware timestamps to America/New_York and then strip timezone for the external engine.
Required columns: datetime/open/high/low/close/volume.

### Economic holdout window
ONLY trades with entry timestamps from **2026-08-03 00:00 ET through 2026-08-20 23:59:59 ET** count.
Data before Aug 3 are warmup/QA only.
No August outcome has been used to modify the pinned model in this research.

## Source-quality gate BEFORE economic interpretation
Use overlapping late-July data to compare Yahoo to two existing independent references:
1. GetData minute proxy (exact archived snapshot SHA `232fbc18375e6475dbe3b99e6e1504da69c58a962aa7a358b14f4e2b61cf229d`) across Jul 22-27, 09:30-15:59 ET.
2. True MNQ trade ledger from `dng-nguyn/mnq-intraday-momentum-backtest`, variant `eta_r1`, k=300, for Jul 22-27 at 15:30 entry and 15:59 exit.

QA pass requires all:
- >= 3 overlapping RTH days Yahoo vs GetData.
- >= 900 overlapping one-minute bars.
- Median absolute Yahoo/GetData CLOSE difference <= 0.50 NQ point.
- >= 95% of overlapping CLOSE bars within 1.00 NQ point.
- On true-ledger overlap days, median absolute Yahoo vs true-MNQ 15:30 entry difference <= 1.00 point.
- Median absolute Yahoo vs true-MNQ 15:59 exit difference <= 1.00 point.

If QA fails, economic results may be computed for debugging but terminal status is `DATA_QA_FAIL_NO_ECONOMIC_INTERPRETATION`.

## Daily context
Use the external repository's own historical `NQ_daily.csv` as pre-August daily context, append daily RTH bars built from Yahoo recent data, de-duplicate dates preferring Yahoo on overlaps, and pass this combined file through the external public `--nq-daily` path.
Minute-level rolling features use only Yahoo recent minute bars; August begins after enough intraday warmup bars for the external 120-bar features.

## Friction rescore
The pinned external BacktestEngineV2 does not fully charge commissions and only contains a small adverse exit slip. Keep its trade path unchanged, then subtract additional round-trip costs in R:
- PRIMARY: additional **1.0 NQ index point per completed trade**.
- STRESS: additional **2.0 NQ points per completed trade**.
Additional cost in R = extra_points / (risk_ticks × 0.25).

## Predeclared August forward gates
PRIMARY all required:
1. Data QA pass.
2. >= 25 completed trades.
3. >= 1.5 trades per observed August RTH trading day.
4. Mean net expectancy >= +0.10R/trade.
5. Profit factor >= 1.25.
6. Aug 3-11 aggregate net R > 0 AND Aug 12-20 aggregate net R > 0.
7. Closed-trade max drawdown <= 7R.
8. Remove best 10% of trades: remaining mean net expectancy >= 0.

STRESS all required:
9. Mean net expectancy > 0.
10. Profit factor >= 1.10.

Terminal status:
- All pass -> `YAHOO_FORWARD_PASS_JUSTIFIES_LICENSED_CME_VALIDATION`.
- QA passes but economic gates fail -> `YAHOO_FORWARD_NO_GO`.
- QA fails -> `DATA_QA_FAIL_NO_ECONOMIC_INTERPRETATION`.

A PASS is not live authorization and is not a validated strategy. It only justifies the cost/effort of a longer licensed CME post-freeze validation.

No post-outcome model removal, long/short filtering, date exclusion, or parameter rescue is permitted on Aug 3-20 outcomes.