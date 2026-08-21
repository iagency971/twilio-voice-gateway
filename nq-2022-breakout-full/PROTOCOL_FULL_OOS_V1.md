# NQ 2022 Breakout — Full OOS V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/nq-2022-breakout-full-oos-v1`

## Objective
Replicate the externally published NQ opening-range breakout strategy with the author's corrected executable engine on an independent, later NQ 1-minute source. No parameter optimisation or rescue filtering is allowed.

## External strategy provenance
Source: `giovannibrusco/nq-intraday-breakout`.
Pinned engine commit: `c5ed61a8cf61c57e2e612d7c7e080c7ec76c8ce1` (2026-07-28 audit/rebuild merge).
The repository states that the rules were written in MultiCharts in early 2022 and were not changed thereafter; its published historical data ends in April 2025. The pinned 2026 repository audit still uses that historical sample and therefore does not include the independent 2026 source opened here.

We use the repository's corrected conventions (`SimFlags()` defaults) and conservative `entry_mode='stop'`, not the more optimistic legacy close-fill convention.

## Frozen rules
- Instrument: NQ E-mini Nasdaq-100 futures.
- Source bars resampled 1m -> 5m, left-labelled.
- Opening range: 08:30 <= CT < 10:00 CT (09:30-11:00 ET), 90 minutes.
- Entry window: 10:00 through 14:30 CT.
- First break of range high -> LONG; otherwise break of range low -> SHORT (same priority as source engine).
- Stop-fill entry convention; gap through entry fills at the bar open.
- Stop = 100 NQ points.
- Target = 200 NQ points.
- Max 2 entries per trading day.
- No stop/target exit on the entry bar.
- Gap-aware exits on subsequent 5m bars.
- LONG can remain open up to 5 CME trading sessions; corrected engine exits max-hold at the final eligible session close.
- SHORT is closed by the source engine's per-day session close convention.
- Full Globex bars are scanned so overnight long stop/target events are observable.
- CME trading-day mapping enabled.
- No DOW/month/volatility/news/trend filters.
- No parameter sweep.

## Independent data
Source: public `axb0306/cme-futures-ohlc`, file `NQ/NQ_1min_20260120_20260415.csv`.
Timestamps are treated as UTC, converted to America/Chicago, then made timezone-naive for the external engine's expected CT convention.
Coverage: 2026-01-20 through 2026-04-15, after the external repository's published historical sample ending April 2025.

To avoid artificial forced closure at the dataset boundary, performance gates use only trades with entry time <= 2026-04-08 CT. The remaining source data through 2026-04-15 is retained solely to permit up to five trading sessions of natural exits for those entries. Late entries after 2026-04-08 are not included in evaluation metrics.

## Costs
PRIMARY = external corrected default: $20.00 per contract round turn ($2.50/side commissions+fees + 1.5 ticks/side slippage).
STRESS = same commissions+fees with 4 ticks/side slippage = $45.00 round turn.

Stage-1 evaluation is per-contract. R = $2,000 stop risk per NQ contract.

## Predeclared viability gates
PRIMARY must satisfy all:
1. >= 25 completed evaluated trades.
2. >= 2.0 completed trades per 5 trading days (frequency proxy for prop use).
3. Mean net expectancy >= +0.10R/trade.
4. Profit factor >= 1.30.
5. At least 2 positive calendar months among February, March, and April-to-cutoff with trades.
6. Closed-trade max drawdown <= 8R.

STRESS must satisfy:
7. Mean expectancy > 0.
8. Profit factor >= 1.15.

If all pass: `PASS_FOR_PROPFIRM_SIZING`.
Else: `NO_GO_OR_INCONCLUSIVE` and this 2026 OOS sample cannot be used for tuning.

## Diagnostics (not rescue filters)
Report long vs short, exit reason, month, losing streak, average win/loss, and concentration. These may generate a future independent hypothesis but may not rescue this frozen strategy on the opened 2026 sample.
