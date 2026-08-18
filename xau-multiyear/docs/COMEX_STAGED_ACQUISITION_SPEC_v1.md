# COMEX staged acquisition specification v1

Date: 2026-08-18
Status: frozen before any COMEX market-data download.

## Principle

Historical COMEX acquisition is staged to avoid paying for the complete GC tape before its incremental value is known. Staging must not turn a small first sample into an unjustified null conclusion. Every extension is governed by predeclared precision/effective-sample triggers, never by whether the observed effect is favorable.

All 1,274,307 XAUUSD events remain in the canonical universe. Continuous GC M1/BBO context is intended for the complete universe; detailed tick flow is sampled only where necessary.

## Stage 0 — broad inexpensive context + unbiased detailed-flow discovery

Acquire:

1. complete GC `ohlcv-1m` continuous history;
2. complete GC `bbo-1m` continuous history;
3. complete trade tape for frozen full-session panel tier 2 (rank <=2 within year x quarter x XAU-volatility tercile; approximately 357 sessions in the preliminary plan);
4. supplemental local `trades` windows for every rare family confluence not already covered by those sessions.

Rare confluences means every multi-family signature except the three abundant FVG pairs:
- DISPLACEMENT_ORIGIN+FVG
- OBJECTIVE_LIQUIDITY+FVG
- MEMORY+FVG

Therefore all DOZ+OBJECTIVE observations are preserved in detailed-flow coverage, along with DOZ+MEMORY, OBJECTIVE+MEMORY and all higher-order stacks.

No FVG-only supplemental tick windows are required at Stage 0 because the frozen session panel supplies a large outcome-blind FVG sample and every FVG event still has continuous M1/BBO context.

Stage 0 purposes:
- construct COMEX-native session VWAP/profile/CVD zones on a temporally stratified panel;
- test whether broad local trade-flow groups show material incremental information;
- estimate variance, clustering, missing-side rates and realistic effective sample sizes;
- establish the precision required for the next acquisition stage.

Stage 0 is NOT permitted to declare an untested family or microstructure group useless merely because a within-family cell is underpowered.

## Stage 1 — precision extension

If Stage 0 detailed-flow estimates do not meet the frozen precision criteria, extend deterministic local coverage outside the already-purchased sessions to total detailed-flow targets:

Pure DOZ / OBJECTIVE / MEMORY, each:
- DEV: 1,000
- VALIDATION: 500
- COMEX_FEATURE_HOLDOUT: 500

Abundant FVG-pair confluences, each:
- DEV: 750
- VALIDATION: 375
- COMEX_FEATURE_HOLDOUT: 375

Rare confluences remain complete, as already required at Stage 0.

## Stage 2 — full precision target

If Stage 1 remains insufficient under the same predeclared precision/effective-sample rule, extend to the existing full targets from `COMEX_SUPPLEMENT_SAMPLING_SPEC_v1.md`:

Pure DOZ / OBJECTIVE / MEMORY, each:
- DEV 2,000
- VALIDATION 1,000
- HOLDOUT 1,000

Abundant FVG-pair confluences, each:
- DEV 1,500
- VALIDATION 750
- HOLDOUT 750

Again, existing ranks are only extended; observations cannot be cherry-picked after COMEX is inspected.

## Precision trigger

For an effect that will be used operationally, detailed-flow acquisition is extended when either of the following remains true after cluster-aware estimation:

- the 95% confidence interval for a primary standardized incremental effect is wider than the preregistered practical-equivalence region; or
- effective sample size after temporal/session clustering is below the preregistered minimum for the claimed effect size.

The practical-equivalence region and model-specific minimum effective sample sizes must be fixed after Stage 0 variance estimation but before Stage 1 outcomes are inspected. This is a variance-design step, not a threshold chosen to preserve a favorable result.

## Acquisition windows

Supplemental local trades use the audited scientific window contact -30 minutes through contact +16 minutes. Actual Databento request bounds are snapped outward to 10-minute boundaries before cost quoting/acquisition. Adjacent request envelopes may be merged with at most a 30-minute gap. Only the causal scientific sub-window and each model's predictor cutoff are admissible in features.

## Cost gate

Every stage requires an exact metadata cost manifest with `download_performed=false`. No transition from metadata quoting to market-data acquisition occurs without explicit user authorization.
