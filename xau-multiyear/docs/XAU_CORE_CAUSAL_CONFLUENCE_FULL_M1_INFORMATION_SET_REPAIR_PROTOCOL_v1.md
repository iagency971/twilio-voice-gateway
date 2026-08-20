# XAU CORE CAUSAL CONFLUENCE FULL M1 INFORMATION-SET REPAIR PROTOCOL v1

Date frozen: 2026-08-20
Branch: `agent/xau-core-evidence-audit-v1`
Status: `FROZEN_BEFORE_FULL_M1_INFORMATION_SET_SUPPORT_AND_PNL`
Authority: Pro decision `B — REPAIR_PREOUTCOME` after the timeframe-aligned 766-event freeze.

## 1. Purpose

Repair only the remaining M1 information-availability defects before any P&L is opened:

1. M1-derived FVG and Memory zones may not be known on the same start-stamped M1 whose completed OHLC forms/confirms them;
2. Memory multi-scale deduplication may not use a later larger-scale confirmation to rewrite an earlier activation;
3. round-number selection from a completed M1 close may not be known until after that M1 completes;
4. widths used at zone activation must use information available at the activation open, not that minute's close spread;
5. the entry minute must be selected from opening BID/ASK quote availability only, never from that minute's later high/low/close.

The prior timeframe-aligned preoutcome freeze is invalid for outcome opening:

- freeze manifest SHA-256: `71f3f68e918ffa2188a8fb2ce4d1c620a0aac87bef3e56b679bd318f90c65162`;
- event manifest SHA-256: `dfd2b5e83d524e188f7482764b7bc05e04cbbbcd8fc6aa72fa61e5798f4d7724`;
- artifact freeze commit: `dd7e848ff5f35cc2e63729f341ec50a92fc2303e`.

No outcome from this invalidated population may be opened.

## 2. Frozen information-time semantics

The historical input remains start-stamped UTC M1 BID/ASK OHLC.

For any rule using the complete high, low or close of a source M1 stamped `t`:

`information_available_time >= t + 1 minute`.

When the exact `t+1` row has no valid opening BID/ASK quote, availability is postponed to the first later row with a valid opening quote.

A valid opening quote requires:

- finite `open_bid`;
- finite `open_ask`;
- both strictly positive;
- `open_ask >= open_bid`.

No high, low or close from the candidate availability/entry minute may establish that the opening quote was available.

## 3. DOZ repair retained unchanged

The prior DOZ timeframe alignment remains frozen:

- `m1_timestamp_semantics = BAR_START_UTC`;
- `resample_closed = left`;
- `resample_label = right`;
- `doz_known_time_semantics = HTF_BAR_CLOSE_BOUNDARY`;
- M15 label 13:15 uses source M1 starts 13:00..13:14;
- M30 label 13:30 uses 13:00..13:29;
- H1 label 14:00 uses 13:00..13:59;
- `source_last_m1_timestamp_used < doz_known_time` for every generated DOZ.

All previous direct-pair, causal-confluence, irreversible CLEAN_REJECTION and prefix-invariance rules remain unchanged.

## 4. M1 FVG availability

A 3-bar FVG whose third/source-completing M1 is stamped `t` may use that completed bar's OHLC for geometry, but:

- `source_last_m1_timestamp_used = t`;
- `information_available_time = first valid opening quote at or after t + 1 minute`;
- `known_time = information_available_time`;
- first contact may not precede `known_time`.

A FVG can therefore never be formed and contacted on the same source M1.

## 5. Directional-change / Memory availability and streaming deduplication

A directional-change confirmation using the completed high/low/close of M1 `t` has:

- `source_last_m1_timestamp_used = t`;
- `information_available_time = first valid opening quote at or after t + 1 minute`;
- `known_time = information_available_time`.

For repeated `(origin_time, kind)` confirmations across delta scales:

1. retain the earliest causal confirmation time permanently;
2. if several scales confirm at that exact same causal time, metadata may use the largest simultaneously-known scale;
3. confirmations at later times may not delete, move, replace or count as a new constituent;
4. later confirmations may not alter the historical activation time used by Memory clustering.

This rule must be prefix invariant.

## 6. Round-number availability

A round-number candidate selected from the close of source M1 `t` has:

- `source_last_m1_timestamp_used = t`;
- `information_available_time = first valid opening quote at or after t + 1 minute`;
- `known_time = information_available_time`.

No contact before that time is allowed.

## 7. Previous-period/session Objective Liquidity

Previous-day/week/session highs/lows remain structurally unchanged.

For any completed source period, the final source M1 is allowed to contribute only after it completes. The level becomes known at the first valid opening BID/ASK quote at or after the source information boundary.

The zone width at activation is computed only from information available at that activation open.

## 8. Causal zone width

For all point-width zones that use `point_half_width` semantics, the spread component at activation time `t` is frozen as:

`open_spread(t) = open_ask(t) - open_bid(t)`.

The width is:

`max(2 * open_spread(t), point_zone_sigma_mult * sigma60(t))`.

`robust_sigma60` remains the existing shifted causal series.

The generic close-based `spread` column may not determine a zone width at its own activation open.

Changing only the later close spread of an activation M1 must not change that zone's width.

## 9. Opening-quote entry eligibility

The causal CLEAN_REJECTION confirmation rule remains unchanged.

Entry eligibility is the first row under the inherited next-minute/max-wait timing rule whose opening quote is valid under section 2.

The entry selector may use only:

- row timestamp;
- `open_bid`;
- `open_ask`.

It may not use the entry minute's high, low, close, close spread, or any later bar.

The frozen direction remains the anchor's effective side:

- SUPPORT -> LONG;
- RESISTANCE -> SHORT;
- existing neutral-side resolution unchanged where applicable.

No entry price, stop, target, exit or P&L is computed in this protocol.

## 10. Zone/contact provenance manifest

For every generated zone that has a raw first contact in any family participating in inclusion or exclusion (`DISPLACEMENT_ORIGIN`, `OBJECTIVE_LIQUIDITY`, `MEMORY`, `FVG`), persist a provenance row containing at minimum:

- zone_id;
- family;
- variant;
- source_tf;
- `source_last_m1_timestamp_used`;
- `information_available_time`;
- `known_time`;
- `first_contact_time`;
- `provenance_pass`.

Required ordering:

`source_last_m1_timestamp_used < information_available_time <= known_time <= first_contact_time`.

For DOZ, the HTF close boundary is the information-availability time and the already-frozen HTF source provenance remains authoritative.

The per-year provenance manifest may be stored compressed, but its row count and SHA-256 must be bound in the annual summary and aggregate freeze.

## 11. Mandatory hard gates

Before any P&L may be opened, aggregate across 2011–2025 and require:

- `all_zone_information_time_violations = 0`;
- `m1_formation_bar_contact_violations = 0`;
- `memory_prefix_invariance_violations = 0`;
- `zone_width_information_violations = 0`;
- `entry_open_quote_causality_violations = 0`;
- `doz_provenance_violations = 0`;
- `event_doz_provenance_violations = 0`;
- `prefix_invariance_violations = 0`;
- `timing_integrity_violations = 0`;
- `duplicate_event_ids = 0`;
- deterministic raw-contact shuffle identity PASS;
- at least 200 entry candidates;
- candidates in at least 12 of 15 target years.

Failure status:

`CAUSAL_CORE_PREOUTCOME_FULL_M1_INFORMATION_SET_SUPPORT_FAIL`.

Pass status:

`CAUSAL_CORE_PREOUTCOME_FULL_M1_INFORMATION_SET_READY_FOR_PNL`.

## 12. Mandatory unit/prefix tests

The precheck must prove at minimum:

1. a FVG completed on M1 10:00 cannot be known or contacted before 10:01;
2. a Memory turn confirmed by M1 10:00 cannot affect a pair at 10:00;
3. adding a later larger delta confirmation cannot delete or move an earlier Memory activation;
4. changing only the activation minute's close spread cannot change its point-zone width;
5. changing only the entry minute's later high/low/close cannot change entry existence, timestamp or opening quote;
6. prior DOZ M15/M30/H1 alignment tests remain PASS;
7. prior irreversible CLEAN_REJECTION and direct-pair tests remain PASS.

## 13. Strategy construction otherwise unchanged

No strategy parameter or subgroup rule is changed:

- DOZ timeframes: 15min / 30min / 1h;
- DOZ variants unchanged;
- Objective Liquidity families/subtypes unchanged;
- direct DOZ-Objective overlap >= 0.50;
- contact-time gap <= 2 minutes;
- causal Memory/FVG exclusion remains the same concept, now with corrected information times;
- deterministic first-completion deduplication unchanged;
- irreversible causal CLEAN_REJECTION unchanged;
- adverse same-M1 breach/reclaim ambiguity unchanged;
- no session, direction, age, timeframe, variant, side-relation or RR filter.

## 14. Required freeze metadata

The aggregate freeze must bind:

- prior invalidated freeze/event-manifest hashes;
- aggregate repaired event-manifest hash;
- all annual event-manifest hashes;
- all annual zone/contact provenance-manifest hashes;
- implementation dependency hashes;
- input hashes;
- all hard-gate counts;
- `pnl_inspected_or_used = false`;
- `tp_sl_exit_simulated = false`;
- `new_market_data_spend = 0`;
- `mandatory_stop = STOP_BEFORE_PNL`.

## 15. Outcome prohibition and no-rescue rule

This protocol authorizes no TP, SL, target, exit, gross-R, net-R, PF, winrate, drawdown or economic comparison.

During the repair it is forbidden to change or select:

- LONG/SHORT;
- session or session transition;
- M15/M30/H1;
- zone age;
- DOZ variant;
- Objective subtype;
- SAME_SIDE;
- overlap threshold;
- 2-minute confluence window;
- CLEAN_REJECTION trigger;
- RR;
- costs;
- M5;
- COMEX.

New market-data spend: `0 EUR`.

## 16. Mandatory stop

After a successful full-M1-information-set preoutcome freeze, STOP before P&L and return the new hashes for Pro review.
