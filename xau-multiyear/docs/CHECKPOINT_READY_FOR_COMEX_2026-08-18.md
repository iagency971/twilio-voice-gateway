# XAUUSD Reaction Zone Research — Ready for COMEX layer

Date: 2026-08-18 UTC
Branch: `agent/xau-multiyear-research`

## Canonical state

### Phase A — zone information

2011–2025 price-defined event study remains valid and unchanged by broker-cost work.

Robust pure-family findings at the primary 0.50 sigma reaction threshold:
- OBJECTIVE_LIQUIDITY: strong positive reaction lift, 15/15 positive annual windows.
- DISPLACEMENT_ORIGIN: strong positive reaction lift, 15/15 positive annual windows.
- MEMORY: smaller and less stable positive effect.
- FVG_3BAR standalone: approximately flat/slightly negative; not supported as a general reaction-zone qualifier.

### Phase B — behavior

The old permissive REJECTED label was replaced by causal behavior classes including CLEAN_REJECTION, FAILED_AUCTION and ACCEPTED_BREAK.

DOZ-type contacts often behave as clean rejections; objective levels contain more true breaches/sweeps. No universal MSS/FVG trigger is assumed.

### Corrected Vantage Phase C

The old broker-economic NO_GO based on Dukascopy BID/ASK plus 22 USD RT is superseded.

Corrected Vantage-like execution scenarios:
- primary: fixed 0.11 USD spread + 6 USD RT/100oz lot;
- sensitivity: 0.10 + 6;
- sensitivity: 0.12 + 6;
- stress: 0.18 + 9.

The corrected 2025 gate reproduced exactly 80,617 research events before execution overlay, proving zone/behavior parity.

The frozen 2011–2025 multiyear gate produced 8 survivors.

Core plateau: `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL` survives at every neighboring target R in 0.5, 1.0, 1.5, 2.0, 2.5 and 3.0. The plateau remains positive under the stress execution scenario. No single RR is selected from this plateau.

Two risk-floor TOUCH_NEXT_OPEN cells also survived historically, but are secondary.

### May–June 2026 temporal P&L holdout

Frozen target window: 2026-05-01 through 2026-06-30 00:00 UTC.

- target research events: 11,447
- `DOZ_OBJECTIVE_ONLY` events: 6
- executable core CLEAN_REJECTION trades: 0

Therefore the core plateau is **INCONCLUSIVE / NOT TESTABLE** on this short holdout because no qualifying trade occurred. It is not a negative expectancy observation.

The two secondary TOUCH_NEXT_OPEN survivors produced 4 trades each, with 0 TP, 3 SL and 1 TIME; net approximately -0.79R/trade in the primary Vantage scenario. This is weak negative evidence only because N=4.

## Current scientific conclusion

A serious historical price-defined candidate exists:

`DISPLACEMENT_ORIGIN + OBJECTIVE_LIQUIDITY + CLEAN_REJECTION`

under a corrected Vantage-like execution model.

It is **not live-ready** because:
1. execution is a fixed-spread Vantage-like overlay around Dukascopy mid, not historical Vantage tick data;
2. centralized COMEX/GC information has not yet been added;
3. no genuinely prospective virgin block has yet validated the final specification.

## Next locked layer — COMEX/GC incremental value

Purpose: test whether centralized futures information improves discrimination of the already-defined price-zone candidates. COMEX data is an augmentation, not a replacement for the XAUUSD execution feed.

Frozen initial source/request architecture:
- provider: Databento historical;
- dataset: `GLBX.MDP3`;
- continuous symbol: `GC.v.0`;
- first schema: `trades` (true executed futures volume / time and sales);
- `mbp-1` only if trades/volume features add incremental out-of-sample value;
- `mbo` only if top-of-book results justify the additional granularity.

Cost-control rule:
- run metadata cost / record-count / billable-size checks first;
- perform **no paid download before exact cost is known**;
- historical download remains blocked until a user-authorized Databento API key is available as the GitHub Actions secret `DATABENTO_API_KEY`.

No Databento market-data download has been performed at this checkpoint.
