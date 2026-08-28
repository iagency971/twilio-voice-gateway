# XAUUSD standalone Z4-gap BR70 SELL — Dukascopy BID/ASK + FTMO commission prereg v1.0

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`
Status: **FROZEN BEFORE BID/ASK EXECUTION OUTCOMES**

## Purpose

Validate the already frozen standalone `Z4-gap + bearish BR70 SELL` trade ledger using executable BID/ASK prices instead of BID-only structural outcomes. This stage may not change signal selection, sessions, Z4 geometry, trigger definition, target, invalidation level, or trade ordering.

The source trade ledgers are immutable artifacts from workflow run `33203080123` (`z4-gap-br70-US`, `z4-gap-br70-ASIA_BROAD`, `z4-gap-br70-ASIA_CORE_STANDALONE`, `z4-gap-br70-EUROPE`).

## Market-data source

Use the same Dukascopy XAUUSD M1 dataset family from `kevingtlin/Market-Data-Lab`, pinned to repository commit:

`3fbaf3280338474b379e3a01ac3396f85d4a60be`

Months: `2024-08` through `2026-07` inclusive.

For every month download both:
- `xauusd/bid/m1/xauusd_bid_m1_YYYY_MM.csv`
- `xauusd/ask/m1/xauusd_ask_m1_YYYY_MM.csv`

BID files must pass the previously frozen SHA-256 values in `cadence-sensitivity/c5-replication-v0-2/XAUUSD_Z4_C5_HISTORICAL_SOURCE_MANIFEST_v0_2.json`.
ASK files have no prior project hash manifest; compute and freeze their SHA-256 values in this run. Source commit pinning makes the source immutable.

Merge BID and ASK by exact UTC millisecond timestamp using an inner join. Report alignment coverage. Every frozen trade entry timestamp must exist on both sides or the run fails.

## Frozen executable SELL convention

For every existing frozen SELL signal:

1. Entry time remains the next M1 open already frozen in the source ledger.
2. Executable short entry price = **BID open** at entry timestamp.
3. Structural target remains the already frozen lower-Z4 upper boundary `target_zhi`.
4. Executable TP occurs only when **ASK low <= target_zhi**. If so, buy-to-cover fill = exactly `target_zhi` (limit-fill assumption).
5. Structural invalidation trigger remains **BID close > stop_zlo**, where `stop_zlo` is the lower boundary of the frozen upper Z4.
6. On confirmed invalidation, executable buy-to-cover fill = **ASK close** of that M1.
7. If executable TP and BID close invalidation occur in the same M1, use conservative ordering: **invalidation first**, exit at ASK close.
8. If neither event occurs by the frozen session end, liquidate at **ASK close** of the final M1 in that session.
9. No carry beyond session end.
10. No trade filter, E-zone condition, RR floor, score, hour subgroup, or session selection may be introduced.

## R denominator

Structural initial risk per oz is frozen as:

`risk_usd_per_oz = stop_zlo - entry_bid_open`

Require `risk_usd_per_oz > 0`.

Gross realized P&L per oz:

`gross_pnl = entry_bid_open - executable_exit_ask_or_target`

Gross realized R:

`gross_R = gross_pnl / risk_usd_per_oz`

This allows confirmed-close invalidations to lose more than 1R when price closes beyond the structural boundary; this is intentional and more execution-realistic than the earlier structural -1R abstraction.

## FTMO commission

Use **current FTMO Metals CFD commission uniformly over H1 and H2** to answer whether the historical setup survives today's commission schedule:

- `0.0007%` of notional volume **per side**;
- decimal rate per side = `0.000007`.

Source: FTMO Trading Update 25 Sep 2025 / current Metals CFD commission structure.

Commission per oz:

`commission_usd = 0.000007 * entry_bid_open + 0.000007 * exit_price`

Net R before extra slippage:

`net_R = (gross_pnl - commission_usd) / risk_usd_per_oz`

Dukascopy BID/ASK already embeds the source-observed spread. Do **not** subtract an additional synthetic spread.

## Extra-slippage diagnostic

In addition to exact BID/ASK + commission, report a deterministic extra round-trip adverse slippage sensitivity of:

- $0.00/oz
- $0.02/oz
- $0.05/oz
- $0.10/oz

For each level subtract `extra_slippage_usd / risk_usd_per_oz` from net R. This is diagnostic only and is not a fitted parameter.

## Prespecified outputs

For each session and H1/H2, plus pooled descriptive results:

- trade count;
- executable TP / invalidation / session liquidation counts;
- gross realized mean R;
- mean R after current FTMO commission;
- mean R after commission + each extra-slippage level;
- profit factor in net R after commission;
- entry BID/ASK spread distribution (median, p90, p95, p99, mean) using `ask_open - bid_open`;
- exit spread distribution where an exact ASK/BID close pair exists;
- initial risk $/oz distribution;
- one-position-at-a-time results using the same deterministic chronological rule as prior diagnostics;
- H1 vs H2 stability.

## Interpretation gate

This remains retrospective/exploratory because the standalone rule was formulated after the E-vs-control study.

A future confirmation candidate exists only if, **after exact BID/ASK + current FTMO commission and with one position at a time**, pooled expectancy is > 0 in both H1 and H2 and at least 3 of 4 sessions are > 0 in both halves. No subgroup may be selected after reading this run.

Production authorization from this study: **NONE_RETROSPECTIVE_BIDASK_EXECUTION_VALIDATION**.
