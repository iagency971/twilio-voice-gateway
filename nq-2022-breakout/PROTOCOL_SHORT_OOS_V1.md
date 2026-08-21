# NQ 2022 Breakout — SHORT OOS V1

Status before outcomes: `PREOUTCOME_FROZEN`
Branch: `agent/nq-2022-breakout-short-oos-v1`

## Why SHORT-only
The externally published 2022-rule strategy allows LONG positions to remain open up to five sessions, which requires complete Globex overnight data. Our independent 2026 GetData source is RTH/extended cash-session data and cannot safely observe overnight long stops/targets. SHORT positions in the published rules are always force-closed by the same-session close, so the SHORT engine can be replicated without hidden overnight path assumptions.

This restriction is based on data observability before outcome inspection, not on short-side performance.

## Frozen external rules
Source reference: giovannibrusco/nq-intraday-breakout, rules asserted written in early 2022.

- Instrument: NQ.
- Resample source 1-minute data to 5-minute bars, left-labelled.
- Opening range: 09:30 <= ET < 11:00 (90 minutes).
- Trading window: 11:00 through 15:30 ET.
- SHORT entry when a 5-minute bar trades below the frozen opening-range low.
- Corrected conservative entry convention: stop fill at breakout level, but if the bar opens below the level, fill at the lower bar open (`min(range_low, bar_open)`).
- Stop: +100 NQ points from entry.
- Target: -200 NQ points from entry.
- Maximum 2 entries per trading day.
- No exit on the entry bar because OHLC ordering is unknowable.
- Gap-aware stop/target fills on subsequent bars.
- Force SHORT flat at last available RTH bar of the day.
- No DOW, month, volatility, trend, news, or discretionary filters.
- No parameter sweep or rescue filter.

## Independent OOS data
GetData public NQ 1-minute sample, 2026-02-02 through 2026-07-31, UTC timestamps converted to America/New_York. This period is after the externally asserted 2022 rule freeze and after the original published historical sample ending April 2025.

## Costs
1 NQ contract for edge measurement only; point value $20.

PRIMARY: published corrected convention = $20 round turn per completed trade (includes $2.50/side all-in commission + 1.5 ticks/side slippage).
STRESS: $45 round turn per completed trade (same commissions + 4 ticks/side slippage).

Costs are subtracted from per-contract P&L. Stage 1 does not optimise sizing.

## Metrics / gates
R = $2,000 published stop risk per contract.

PRIMARY must satisfy all:
1. >= 20 completed trades.
2. Mean net expectancy >= +0.10R/trade.
3. Profit factor >= 1.25.
4. At least 4 positive calendar months with trades.
5. Closed-trade max drawdown <= 8R.
6. May-Jul mean expectancy >= +0.05R/trade.

STRESS must satisfy:
7. Mean expectancy > 0.
8. Profit factor >= 1.15.

If all pass: `PASS_FOR_PROPFIRM_SIZING`.
Otherwise: `NO_GO_OR_INCONCLUSIVE`; no tuning on this 2026 sample.

## Stage 2 only after PASS
Translate the fixed signal to MNQ/NQ sizing and simulate explicit challenge/funded drawdown rules. Signal parameters remain unchanged.
