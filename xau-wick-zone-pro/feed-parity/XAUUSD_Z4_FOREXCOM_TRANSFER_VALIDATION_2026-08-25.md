# XAUUSD Z4 — FOREXCOM Transfer Validation

**Date:** 2026-08-25  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Decision:** `FOREXCOM_TRANSFER_OPERATIONALLY_VALIDATED`

## Decision

`FOREXCOM:XAUUSD` is authorized as the **operational TradingView feed for Z4 C5 transfer**.

This authorization is based on an outcome-blind, preregistered feed-transfer pilot using the exact TradingView `FOREXCOM:XAUUSD` M1 chart feed and Dukascopy XAUUSD reference data over their common available window. No revisit, reaction, reversal, MFE/MAE, RR or P&L outcome entered the gate.

No FOREXCOM-specific model refit, coefficient change, normalization refit or R remapping was allowed or used.

The scientific reference remains Dukascopy XAUUSD BID. FOREXCOM is validated here as a **transfer/operational feed**, not redefined as the original scientific-development feed.

## Source identity

TradingView resolved the source as:

- symbol: `FOREXCOM:XAUUSD`;
- exchange/source: `FOREXCOM` / FOREX.com;
- provider: GAIN;
- type: Gold/USD CFD;
- M1 bar source: `mid`.

Because TradingView supplies midpoint bars, the primary transfer pair was preregistered as **Dukascopy synthetic MID -> FOREXCOM MID**. Dukascopy BID -> FOREXCOM MID was a support/control comparison and could not rescue a primary failure.

## Frozen transfer gate result

Overall verdict: `PILOT_PASS_TRANSFER_VIABLE`.

Common raw-feed window: 2026-08-16 22:01 UTC -> 2026-08-20 23:58 UTC.

Mature C5 evaluation begins at 2026-08-18 07:00 UTC after LOOKBACK=1440 active M1 and the frozen 96-landmark C5 warm-up.

### Raw feed parity — PASS

Primary Dukascopy MID -> FOREXCOM MID:

- FOREXCOM timestamp coverage: 99.9291%;
- common active M1: 5,634;
- consecutive 1-minute return pairs: 5,625;
- return Pearson: 0.995321;
- return Spearman: 0.992149;
- bar-range Pearson: 0.992720;
- bar-range Spearman: 0.982842.

All preregistered raw-feed criteria pass.

### Z4 geometry transfer — PASS

On 744 mature common C5 timestamps:

- Dukascopy reference zones: 6,087;
- FOREXCOM target zones: 6,171;
- matched pairs: 5,789;
- Dukascopy zone match rate: 95.1043%;
- FOREXCOM zone match rate: 93.8098%;
- close-aligned IoU median: 0.922179;
- close-aligned IoU p10: 0.758748;
- close-aligned center error median: 0.067797 vseg;
- close-aligned center error p95: 0.246508 vseg.

Every preregistered geometry-transfer threshold passes.

### Frozen M0GL score transfer — PASS

The unchanged Dukascopy BID C5 M0GL model was applied to both native feed feature tables.

- score Pearson: 0.996054;
- score Spearman: 0.997826;
- median absolute score error: 0.004311;
- p95 absolute score error: 0.040992;
- top-1 zone agreement: 84.8118%.

Every preregistered frozen-score criterion passes.

### Frozen R-map transfer — PASS

The existing Dukascopy C5 DEV percentile map was applied unchanged to both feeds.

- R Pearson: 0.997571;
- R Spearman: 0.997826;
- median |delta R_float|: 0.981;
- p95 |delta R_float|: 4.476;
- displayed R within +/-5: 97.5471%;
- within +/-10: 99.9136%;
- within +/-20: 99.9655%.

Every preregistered R-transfer criterion passes.

`R` remains a percentile/rank of frozen revisit-likelihood score. It is not a probability and not reaction strength.

## BID control — PASS

Dukascopy BID -> FOREXCOM MID also independently passes the same transfer criteria:

- Dukascopy zone match: 94.3673%;
- FOREXCOM zone match: 93.6639%;
- relative IoU median: 0.918422;
- score Spearman: 0.997931;
- R Spearman: 0.997931;
- top-1 agreement: 84.5430%.

This strengthens the operational-transfer conclusion but was not used to rescue the primary MID comparison.

## Authorization

Effective immediately for this research project:

- Dukascopy BID remains the scientific reference feed.
- `FOREXCOM:XAUUSD` is **validated for operational Z4 C5 use in TradingView**.
- The frozen C5 model parameters remain unchanged.
- The frozen C5 R map remains unchanged.
- No FOREXCOM calibration layer is introduced.
- LOOKBACK remains 1440 active M1.
- C5 cadence remains 5 minutes.
- WARMUP remains 96 C5 landmarks.

The previously stated `FOREXCOM = transfer assumption only` limitation is superseded by this validation decision.

## Residual limitation

The available unauthenticated TradingView history allowed only a short temporal transfer window. Attempts to obtain arbitrary older ranges and anonymous `prodata` replay history did not provide deeper data.

Therefore this validation does **not** claim that feed parity has been independently replicated across every volatility regime or across a full multi-year sample. That is a residual generalization limitation, not a blocker to the operational feed authorization above.

Any future deeper FOREXCOM dataset should be treated as a replication/monitoring opportunity. It must not trigger silent refitting unless separately preregistered.

## Pine implementation distinction

This document validates the **FOREXCOM feed transfer**, not the TradingView Pine runtime implementation itself.

The current C5 Pine candidate remains subject to its separate runtime implementation gate: Pine v6 compilation, replay stability at confirmed 5-minute snapshots, live confirmed-close behavior, and GRID_LIMIT recovery/re-arm checks.

Feed validation and Pine runtime validation are separate claims and must not be conflated.
