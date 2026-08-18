# XAUUSD Reaction Zone Research — Corrected Vantage May–June 2026 holdout outcome

Date: 2026-08-18 UTC
Branch: `agent/xau-multiyear-research`

## Frozen setup

Target window: 2026-05-01 00:00 UTC to 2026-06-30 00:00 UTC, with causal warm-up before the target.

Only the eight configurations that survived the corrected Vantage 2011–2025 gate were eligible. No new RR, entry, stop, filter, subtype, session, cost model or behavior rule was selected from this holdout.

Execution scenarios were unchanged:
- primary: 0.11 USD fixed spread + 6 USD round-turn commission per 100oz lot;
- sensitivity: 0.10 / 0.12 USD + 6 USD RT;
- stress: 0.18 USD + 9 USD RT.

## Sample size

- all target reaction-zone events: 11,447
- `DOZ_OBJECTIVE_ONLY` events: **6**
- executable `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION` trades: **0**

Therefore the six-cell CLEAN_REJECTION RR plateau has no P&L observation in this two-month target window. Its frozen primary/stress gate cannot be evaluated. The formal gate fields are false because there are no trades, but this is **not evidence of negative expectancy**; it is an absence-of-opportunity / low-power outcome.

## Touch-next-open survivor cells

The two previously frozen TOUCH_NEXT_OPEN risk-floor cells each generated only **4 trades** in the primary scenario:

- `VOL_FLOOR_0.50`, target R 2.5: 0 TP, 3 SL, 1 TIME, average net ≈ **-0.7954R/trade** at 0.11 + 6 USD.
- `VOL_FLOOR_0.75`, target R 3.0: 0 TP, 3 SL, 1 TIME, average net ≈ **-0.7809R/trade** at 0.11 + 6 USD.

Stress results remain similarly negative (~-0.8006R and ~-0.7847R respectively).

Because N=4 per cell, this is weak negative evidence only. It does not overturn the 15-year statistics by itself, but it does not provide temporal confirmation either.

## Interpretation

**CLEAN_REJECTION core family: temporal holdout is INCONCLUSIVE / NOT TESTABLE on this short window due zero trades.**

**TOUCH_NEXT_OPEN secondary cells: NOT CONFIRMED; small-N holdout is negative.**

The corrected 2011–2025 Vantage result therefore remains the main historical evidence: eight cells passed the frozen multiyear gate, with the strongest structural finding being the six-RR plateau `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION`.

This holdout does not promote the strategy to live-ready status.

## Next scientific layer

The next missing information layer is centralized COMEX/GC data. The research question is not to replace the price-defined candidate, but to test whether GC executed volume / auction information and later top-of-book order flow add incremental discrimination between high- and low-quality DOZ + objective-level contacts.

The Databento acquisition is currently cost-check-only and blocked by the absence of a user-authorized `DATABENTO_API_KEY`. No paid market-data download has occurred. Exact cost must be queried before any paid download.