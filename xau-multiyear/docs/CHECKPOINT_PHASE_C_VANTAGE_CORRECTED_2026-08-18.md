# XAUUSD Reaction Zone Research — Corrected Vantage Phase C checkpoint

Date: 2026-08-18 UTC
Branch: `agent/xau-multiyear-research`

## Supersession notice

This checkpoint supersedes the **broker-economic conclusion** of `CHECKPOINT_PHASE_C_NO_GO_2026-08-18.md`.

The old checkpoint remains useful as an audit trail showing that the original execution model was overly punitive and that raw `TOUCH_NEXT_OPEN` could create pathological near-zero risks. It must **not** be used to conclude that the Vantage strategy candidates are NO_GO.

Reason for supersession:

- old execution path used historical Dukascopy BID/ASK plus a 22 USD round-turn commission assumption;
- corrected Vantage-like model uses the unchanged Dukascopy mid-price path for research, but reconstructs execution BID/ASK using fixed Vantage-like spreads and the corrected RAW commission assumption;
- the corrected primary scenario is 0.11 USD spread + 6 USD round-turn commission per 100oz lot;
- sensitivities are 0.10/0.12 USD spread + 6 USD RT;
- stress is 0.18 USD spread + 9 USD RT.

Approximate primary break-even mid move for 1 lot (100oz):

`0.11 + 6/100 = 0.17 USD`.

## Research invariance / parity

Phase A and Phase B were **not recalculated or altered** by the broker-cost correction.

The corrected 2025 Vantage run reproduced exactly **80,617 target events** from the research engine before changing execution quotes. Zone generation and behavior labels remain based on the unchanged mid-price path. Only executable BID/ASK and round-turn commission are replaced by the Vantage-like overlay.

## Corrected 2011–2025 Vantage gate

Years: 2011–2025 (15 annual target windows with causal warm-up).

Frozen gate evaluated the complete corrected execution surface under:

- primary 0.11 spread + 6 USD RT;
- sensitivity 0.10 + 6;
- sensitivity 0.12 + 6;
- stress 0.18 + 9.

**Eight cells survive all frozen gate criteria.**

### Core robust plateau: DOZ + objective level + clean rejection

All six neighboring target-R values survive:

| Target R | Trades | Weighted net R primary | Positive years primary | Median annual PF primary | Weighted net R stress | Positive years stress | Median annual PF stress |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 | 304 | +0.12043 | 11/15 | 1.5391 | +0.08616 | 11/15 | 1.3298 |
| 1.0 | 304 | +0.25766 | 14/15 | 1.8589 | +0.15952 | 12/15 | 1.3928 |
| 1.5 | 304 | +0.27992 | 13/15 | 1.6629 | +0.18961 | 12/15 | 1.4634 |
| 2.0 | 304 | +0.28849 | 11/15 | 1.7901 | +0.21082 | 10/15 | 1.3172 |
| 2.5 | 304 | +0.26651 | 11/15 | 1.4905 | +0.18597 | 11/15 | 1.4312 |
| 3.0 | 304 | +0.30979 | 12/15 | 1.3324 | +0.20774 | 11/15 | 1.2835 |

This is a **plateau**, not a single isolated optimized RR peak. No target R is selected from this table for live use at this checkpoint.

### Additional surviving touch-next-open cells

Two corrected risk-floor cells also pass the frozen gate:

1. `DOZ_OBJECTIVE_ONLY + TOUCH_NEXT_OPEN + VOL_FLOOR_0.50`, target R 2.5: 755 trades, +0.07047R primary, 10/15 positive years; +0.00590R stress, 8/15 positive years.
2. `DOZ_OBJECTIVE_ONLY + TOUCH_NEXT_OPEN + VOL_FLOOR_0.75`, target R 3.0: 755 trades, +0.06043R primary, 10/15 positive years; +0.03263R stress, 10/15 positive years.

The raw no-floor `TOUCH_NEXT_OPEN` remains audit-only because near-zero risk geometry was proven pathological in 2013.

## Current interpretation

The corrected cost model **reverses the earlier Phase C conclusion**. The data now support a serious price-defined candidate family:

`DISPLACEMENT_ORIGIN + OBJECTIVE_LIQUIDITY + CLEAN_REJECTION`.

It survives a broad RR neighborhood and a materially harsher spread/commission stress scenario over 15 annual windows.

This does **not** yet establish a live-ready strategy.

## Remaining limitations / required work

1. The Vantage execution layer is currently a **fixed symmetric spread overlay** around the historical Dukascopy mid path, not an actual historical Vantage tick/BID-ASK feed. Broker-feed replication remains required.
2. COMEX/GC centralized volume, trades and order-flow are **not yet integrated** into the 2011–2025 strategy result. Their incremental value must be tested separately.
3. May–June 2026 is being used as a frozen temporal P&L confirmation for the eight survivors. It is not fully virgin at the zone-reaction research level, but corrected Vantage P&L was not used to select the eight cells on that target window.
4. A genuinely prospective/virgin validation block remains mandatory after the final specification, including any COMEX feature use, is frozen.
5. No live trading recommendation is made at this checkpoint.

## Scientific rule from here

Do not optimize a single RR from the six-cell clean-rejection plateau. Preserve the plateau through temporal holdout, COMEX incremental-value testing and broker-feed replication before selecting a deployable exit rule.