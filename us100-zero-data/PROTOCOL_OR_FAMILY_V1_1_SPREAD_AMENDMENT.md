# OR Family V1.1 — Spread Unit Amendment

Status: `PRE_DEV_ECONOMICS_FROZEN`

This amendment is written before any 2021–2024 strategy outcome has been calculated and before the sealed 2025 OOS file has been opened.

It changes only the interpretation of the archive `spread` field in `PROTOCOL_OR_FAMILY_V1.md`. All candidate families, opening-range lengths, RRs, time windows, DEV gates, OOS gates and no-rescue rules remain unchanged.

## Reason

The archive format is `time;open;high;low;close;volume;spread`, matching MetaTrader/MqlRates semantics. In MqlRates, `spread` is stored in symbol points. USTEC prices in the archive are quoted to one decimal place, therefore V1.1 freezes `SYMBOL_POINT = 0.1` USTEC index point.

The executable spread used by the backtest is therefore:

`spread_price = recorded_spread * 0.1`.

Example: `spread=2` is interpreted as `0.2` USTEC index point, not 2 index points.

## Execution mapping

The archive OHLC is treated as bid-side OHLC.

PRIMARY:
- long entry = next M1 bid open + `spread_price`; long exits evaluated/executed on bid;
- short entry = next M1 bid open; short stop/target checks use ask-equivalent OHLC (`bid OHLC + spread_price`) and short exits execute at ask.

STRESS doubles `spread_price` everywhere.

No other economic or strategy parameter changes.