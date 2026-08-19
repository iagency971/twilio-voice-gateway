# XAUUSD Reaction Zones — COMEX DEV_RANK1 Native Retest Acquisition Freeze v1

Date: 2026-08-18
Status: FROZEN BEFORE any Stage-2 native-zone market-data quote or download.

## Purpose

This document fixes how the 368 primary terminal COMEX-native levels generated from DEV_RANK1 are allowed to be tested. It does not change the source-level definitions.

Primary source levels are exactly:

- completed-session VWAP;
- completed-session POC;
- completed-session VAH;
- completed-session VAL.

They come from 92 source sessions with usable primary raw tape. Four DEV_RANK1 sessions have no primary source levels because the source session is missing/unusable. Source creation uses no future XAU or COMEX outcome.

The source registry used for any Stage-2 work MUST be `COMEX_DEV_RANK1_NATIVE_SOURCE_LEVELS_V1_1` or later and MUST contain `contact_tick_price` aligned exactly to the GC 0.10 tick. The older published V1 registry is not valid for contact acquisition because VWAP-like exact decimal levels were not yet rounded to an executable GC tick.

## Primary retest horizon

The primary experiment tests only the **next GC auction session after the source session is complete**.

It does not search weeks or months until a level is eventually hit.

For each source level:

- `known_time_utc` is the end of the completed source session;
- the eligible retest session is the first subsequent canonical GC auction session identified independently of the source level price and outcome;
- the source raw `instrument_id` remains fixed;
- if that raw instrument does not trade in the next auction session, the source level has no primary raw contact in that session.

No later session may be substituted because the next-session result is inconvenient.

## Contact definition

The primary contact is:

> the first raw GC trade in the eligible next auction session whose executed trade price equals `contact_tick_price` exactly, on the same raw `source_instrument_id` that created the level.

A contact cannot be confirmed from:

- GC continuous-symbol price;
- XAUUSD price;
- a minute-bar high/low crossing alone;
- a different expiry;
- an adjusted or spread-transposed level.

If no exact trade occurs at the tick during that next auction session, the primary label is `NO_EXACT_CONTACT`.

## Two-stage acquisition allowed

To minimize paid tape without weakening the exact-contact rule, Stage 2 may use a deterministic two-stage acquisition.

### N1 — raw OHLCV-1m screening

Acquire `ohlcv-1m` for the fixed source raw instrument over the full eligible next auction session.

This layer may only answer whether an exact contact is **possible** in each minute:

- if `low > contact_tick_price` or `high < contact_tick_price`, an exact trade at the level is impossible in that bar;
- if `low <= contact_tick_price <= high`, that minute becomes an exact-tape candidate.

A minute-bar crossing NEVER counts as a contact.

If no M1 bar spans the contact tick, the level can be labeled `NO_EXACT_CONTACT` without tick download because OHLCV is derived from executed trades and therefore an exact trade at that price cannot exist outside the observed executed-price range.

### N2 — exact trades only in candidate minutes

For levels with one or more candidate minutes, acquire raw `trades` only for the union of candidate one-minute intervals in chronological order.

All candidate minutes in the eligible session must remain eligible for acquisition; do not stop the cost manifest based on a future result that has not yet been downloaded.

After N2 download:

- scan raw trades chronologically;
- first trade with `price == contact_tick_price` is the primary contact;
- if candidate minutes contain no exact trade at the tick, label `NO_EXACT_CONTACT`.

This makes M1 a lossless screening layer for exact-contact discovery, not a substitute outcome.

## Deduplication

Paid requests may be deduplicated only by market-data identity:

- same raw `instrument_id`;
- same eligible session;
- overlapping time interval;
- same schema.

Levels and source sessions must retain their own IDs after a shared request is downloaded.

Deduplication may not depend on whether a level later reacts profitably.

## Outcome separation

Three quantities remain separate:

1. probability of an exact next-session raw contact;
2. XAU/GC reaction conditional on exact contact;
3. economic entry-model expectancy conditional on a causally specified entry after contact.

A level that is never contacted is not a zero-R trade.

## Causality

The terminal source level is known only after the source session closes.

No data from the eligible next session may alter:

- the source level price;
- the source raw instrument;
- the level type;
- the source session inclusion.

For any post-contact entry model, COMEX information used to select the entry must be truncated at that model's frozen decision time. Post-entry data are outcome data only.

## Analysis unit and controls

The independent cluster remains the source/retest trading date, not an individual level.

VWAP/POC/VAH/VAL from the same source session are correlated observations and must not be treated as four independent days.

Primary native-zone comparisons must use matched controls frozen before outcome inspection, preserving at minimum:

- year;
- session/time-of-day of contact;
- direction/approach where applicable;
- volatility context.

No level type is removed because its DEV_RANK1 result is weak.

## Financial gates

No Stage-2 native-zone market data are authorized by this document.

The sequence is mandatory:

1. regenerate and QA the V1.1 source registry at zero market-data cost;
2. identify the eligible next auction session for each source session using already-owned continuous context / canonical session rules only;
3. create and hash the raw OHLCV-1m N1 request manifest;
4. run `metadata.get_cost()` only and publish exact N1 cost with `download_performed=false`;
5. stop for explicit user authorization;
6. only after N1 is downloaded, generate N2 candidate-minute trade requests;
7. run a second `metadata.get_cost()` for N2 and stop again before any N2 download.

No N2 cost estimate may be invented before N1 tells us the actual candidate minutes.

## Locked blocks

DEV_RANK2, RETRO_CONFIRM and LOCKED_COMEX_TEST remain closed throughout this DEV_RANK1 native-zone Stage-2 preparation.
