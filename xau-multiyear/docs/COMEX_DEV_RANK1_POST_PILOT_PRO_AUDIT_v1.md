# XAUUSD Reaction Zones — COMEX DEV_RANK1 post-pilot Pro audit v1

Date: 2026-08-18
Branch: `agent/xau-comex-acquisition-plan`
Status: audit/specification only. No market-data download authorized or performed by this audit.

## Verdict

**B — DEV_RANK1 must be modified before purchase.**

The core staged design is viable, but four changes are mandatory before acquisition:

1. Remove `bbo-1m` from the immediate DEV_RANK1 purchase and treat it as a separate optional feature group.
2. Do not exclude all 12 paid pilot sessions uniformly. The six pilot sessions in RETRO_DEV may be used as development observations; the three RETRO_CONFIRM and three LOCKED_COMEX_TEST pilot sessions remain QA-only and must be replaced by the next valid deterministic session in the same `year × quarter × vol_band` stratum.
3. Regenerate inclusion/post-stratification weights after the role/replacement correction. The current `model_poststrat_weight` based on simply removing QA sessions is not the clean original sampling design.
4. Publish a zero-cost pre-acquisition coverage/feasibility table for DEV_RANK1 by family, confluence, behavior, entry model, direction, year, and independent trading-date count.

## Immediate acquisition after corrections

Purchase only:

- `GLBX.MDP3 / GC.v.0 / ohlcv-1m`, 2010-06-06 through 2019-01-01;
- `GLBX.MDP3 / GC.v.0 / trades` for the 92 new DEV_RANK1 sessions.

Use the four already-paid DEV pilot sessions with `panel_rank_v4=1` in the DEV_RANK1 development set, yielding 96 analytical DEV_RANK1 sessions without re-buying them.

Do not purchase now:

- `bbo-1m`;
- additional `tbbo`;
- `bbo-1s`;
- `mbp-1`;
- `mbo`;
- post-entry COMEX data for dynamic exits.

Current metadata quote components:

- DEV `ohlcv-1m`: USD 10.623191446066;
- 92 new DEV_RANK1 `trades` sessions: USD 9.524125277992;
- total current quote: USD 20.147316724058.

Recommended hard cap: **USD 20.16**, with an immediate pre-download re-quote and stop if exceeded.

## Pilot-session role correction

The pilot selected six RETRO_DEV sessions: four rank-1 and two rank-2. These data influenced only development-stage data QA and preprocessing choices, so they may remain in RETRO_DEV.

The three RETRO_CONFIRM and three LOCKED_COMEX_TEST pilot sessions are no longer pristine for strict confirm/test use. Keep them `QA_ONLY`, and select replacements by the already-frozen panel hash within the same `year × quarter × vol_band`, excluding weekends and all pilot dates.

Expected analytical stage sizes after this correction:

- DEV_RANK1: 96 sessions = 92 new + 4 already paid;
- DEV_RANK2: 96 sessions = 94 new + 2 already paid;
- RETRO_CONFIRM: restore the full corrected panel count through same-stratum replacements;
- LOCKED_COMEX_TEST: restore the full corrected panel count through same-stratum replacements.

## Side=N policy

Primary analysis:

- retain native `A`, `B`, and `N` exactly as disseminated;
- never silently impute `N`;
- calculate `native_delta = B - A`;
- calculate `N_volume_share`;
- calculate `delta_lower_bound = B - A - N`;
- calculate `delta_upper_bound = B - A + N`;
- calculate `delta_sign_robust` when the interval excludes zero;
- reset cumulative signed-flow state at session and contract-mapping boundaries.

`N_volume_share` is both a market/data-generation condition and a potential era/time-of-day proxy. It must not be optimized as free alpha without year, contract, and time-of-session controls.

TBBO side recovery remains a secondary sensitivity analysis only. It is not the primary historical truth.

## Authorized Phase-1 feature groups

### Continuous M1 context

- GC returns, range, realized volatility;
- total minute volume and trailing relative-volume baselines;
- minute-of-session seasonality;
- zero-volume/stale-print flags;
- GC–XAU basis and basis change at M1 resolution, with roll/staleness flags.

### Full-session and local trades

- total volume, trade count, tape speed, trade-size distribution;
- exact session-to-date VWAP;
- exact volume-at-price;
- developing POC/VAH/VAL/HVN/LVN using information available up to the decision time;
- completed prior-session profiles;
- native A/B delta, N share, delta bounds, robust sign;
- local 1/5/15/30-minute features;
- clearly named price-impact/absorption proxies, never described as direct resting-liquidity observation.

Not authorized in Phase 1:

- BBO spread/queue imbalance features;
- OFI, replenishment, quote withdrawal;
- full depth/queue position;
- final current-session profile used before session close;
- TBBO-imputed primary delta.

## Causal windows

The uniform local extraction envelope remains `contact -30m` through `contact +16m` for behavior comparison.

Feature values used by a model must stop at its frozen decision time:

- PASSIVE_TOUCH: strictly before contact-bar start;
- TOUCH_NEXT_OPEN: contact-bar close;
- ACCEPTANCE_RETEST: `t0 + 5m` under the current model;
- CLEAN_REJECTION / FAILED_AUCTION / RECLAIM_PULLBACK: actual reclaim-bar close, no later than `t0 + 16m`.

The 120-minute post-entry horizon is outcome labeling, not predictor availability.

## Statistical design

DEV_RANK1 is feature discovery, not final validation.

Mandatory:

- treat trading date/session as the independent cluster;
- use leave-one-year-out development diagnostics;
- preserve `year × quarter × vol_band` sampling weights;
- define both event-level and session-level estimands;
- analyze broad families separately before any pooled model;
- prevent FVG from dominating pooled results through explicit family weighting or hierarchical effects;
- declare rare family × model cells inconclusive rather than negative;
- never select observations or thresholds from known price-only winners.

## Zero-cost gates before download

Publish and hash:

1. corrected session-role/replacement file;
2. regenerated strata weights;
3. DEV_RANK1 coverage matrix by family, exact confluence, behavior, entry model, direction, year, and independent session count;
4. pilot raw-data QA for flags, unexplained sequence/data-quality issues, contract mappings, and session-boundary trimming;
5. feature dictionary with exact formulas, profile binning, value-area algorithm, resets, warm-ups, and causal cutoffs;
6. analysis plan specifying baselines, targets, metrics, clustering, weighting, multiplicity control, and forbidden lookahead.

## Freeze criteria before DEV_RANK2

Before opening DEV_RANK2:

- all raw and session-boundary QA must be resolved;
- side=N policy must remain frozen;
- feature formulas and horizons must be frozen;
- COMEX-native zone definitions and future-retest generation rules must be frozen;
- model class and hyperparameter-selection procedure must be frozen using DEV_RANK1 only;
- all broad POI families remain present; sparse cells are marked inconclusive;
- a dated DEV_RANK1 report and SHA-256 manifest must be committed;
- no DEV_RANK2, RETRO_CONFIRM, or LOCKED_COMEX_TEST COMEX data may have been opened.

DEV_RANK2 is a replication block, not an additional tuning block.

## Budget

Current corrected immediate quote excluding `bbo-1m`: USD 20.147316724058.

Recommended acquisition hard cap: **USD 20.16**.

With the already-observed pilot spend of USD 4.01, projected cumulative project spend after this modified DEV_RANK1 purchase is USD 24.157316724058, leaving USD 100.842683275942 of a nominal USD 125 credit.
