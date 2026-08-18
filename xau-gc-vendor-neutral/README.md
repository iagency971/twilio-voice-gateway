# XAU/GC vendor-neutral ingestion

Goal: enrich all XAUUSD reaction-zone events with GC/COMEX data without binding the research to one vendor.

Supported source contracts:

1. **Sierra Chart intraday export** — expected CSV header: `Date, Time, Open, High, Low, Last, Volume, NumberOfTrades, BidVolume, AskVolume`. For 1-tick records, `Last` is trade price; `BidVolume`/`AskVolume` identify sell/buy aggressor volume.
2. **Databento GLBX.MDP3 trades/MBP-1** — normalized separately into the same schema.
3. **TradingView GC OHLCV/derived features** — optional validation/live-prototyping source, not the canonical historical tick source.

Canonical normalized output columns:

- `ts_utc`
- `contract`
- `trade_price`
- `trade_size`
- `bid_volume`
- `ask_volume`
- `aggressor` (`SELL`, `BUY`, `UNKNOWN`)
- `source`

Derived 1-minute feature output:

- OHLC
- total volume
- bid volume
- ask volume
- delta (`ask_volume - bid_volume`)
- cumulative/session delta
- trade count
- VWAP
- rolling volume z-scores

Later layers (POC/VAH/VAL/HVN/LVN, basis mapping to XAUUSD, event enrichment) consume only this normalized schema.

Research rule: no strategy family is eliminated solely from price-only results before the GC enrichment experiment has been run on all sufficiently large pre-registered populations.
