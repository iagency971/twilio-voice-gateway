# XAUUSD Reaction Zones — COMEX DEV_RANK1 Roll Policy CANONICAL v2

Date: 2026-08-18
Status: **PRO-APPROVED PRE-ACQUISITION CANONICAL POLICY**.

This document supersedes `COMEX_DEV_RANK1_ROLL_POLICY_CANDIDATE_v1.md` wherever they conflict.

## Verdict

Primary contract architecture for DEV_RANK1:

**DUAL_V0_N0_CAUSAL_ACTIVE**

Sensitivity architectures, frozen before acquisition:

- `N0_FROZEN_ONLY`;
- `V0_FROZEN_ONLY`.

The sensitivity results may not replace the DUAL primary result after outcomes are observed.

## Session-start candidate set

At the canonical GC auction-session start:

1. resolve `GC.v.0` and `GC.n.0` using mappings available at that time;
2. freeze the resulting raw `instrument_id` values for the full session;
3. if both mappings are identical, acquire/use that raw contract once;
4. if mappings differ, acquire both raw contracts;
5. never follow an intraday remapping of either continuous smart symbol for session-profile construction.

Historical session bounds remain:

- before trade date 2015-09-21: 18:00 New York on D-1 through 17:15 New York on D, end-exclusive;
- on/after 2015-09-21: 18:00 New York on D-1 through 17:00 New York on D, end-exclusive.

Holiday/short/closed sessions are retained under the frozen availability policy; they are not replaced merely for low activity.

## Intraday active-contract routing

Routing unit:

`event_uid × target/entry_model × decision_time`.

For a decision timestamp `D`, define:

`M = beginning of the wall-clock minute containing D`.

For each frozen candidate raw contract `c`:

`CumVol_c(D) = sum(size)` for trades satisfying:

- canonical session start <= `ts_event` < `M`;
- raw `instrument_id = c`.

Only fully completed minutes can influence routing.

Routing rule:

1. if V0 and N0 map to the same contract, select that contract;
2. otherwise if `CumVol_V0 > CumVol_N0`, select V0 candidate;
3. otherwise if `CumVol_N0 > CumVol_V0`, select N0 candidate;
4. otherwise select N0 candidate deterministically.

The tie-break therefore covers equal positive cumulative volume and the zero/zero case.

No ratio threshold, minimum volume threshold, minimum warm-up duration, hysteresis parameter or post-hoc switching threshold exists in the primary rule.

## First minutes of a session

Before any completed minute exists, both causal cumulative volumes are treated as zero and N0 wins by the frozen tie-break.

Feature horizons that lack sufficient completed history remain missing/partial under the feature-specification rules. No arbitrary 5/15/30-minute routing warm-up is introduced.

## No contract splicing

Two expiries are never pooled into one CVD, VWAP or volume-at-price profile.

For each decision, after routing selects a raw contract, every B2 tape/profile feature is reconstructed from that selected raw contract only. If another decision later in the same session selects the other candidate, its features are reconstructed independently from that other raw contract's own session history.

No state is transferred from one expiry to the other.

## Data-quality failure during routing

If only one smart-symbol mapping resolves at session start, the available raw contract may be used and an explicit mapping-availability flag is set.

If both mappings resolve but one candidate tape has a blocking data-quality/coverage failure before the decision, the primary DUAL routing result is marked unavailable for that decision. The other contract is **not** silently promoted merely because the first tape is missing or corrupt.

Legitimate zero/low trading activity remains real market information and is not treated as a data failure solely because activity is small.

## B1 continuous context versus B2 active raw tape

B1 continuous M1 context is `GC.n.0 / ohlcv-1m` and must be namespaced as `n0_context_*`.

B2 tape/profile features come from the DUAL-selected raw contract and must be namespaced as `active_raw_*`.

It is forbidden to combine N0 continuous prices with V0 raw volume/delta/profile components as though they were one instrument.

For a selected session whose continuous M1 layer is incomplete, selected-contract M1 OHLCV may be reconstructed deterministically from raw trades and flagged. It does not alter the continuous N0 context series outside that selected-session repair use.

## Terminal COMEX-native source zones

After a source session is complete, full-session traded volume is causal.

On a divergent candidate session, the source raw contract for terminal VWAP/POC/VAH/VAL/HVN/LVN/void levels is:

- candidate with greater full-session `sum(size)`;
- deterministic tie-break N0.

Terminal levels are generated from that single raw contract only.

A native level remains attached to its source raw `instrument_id`. Primary future retest logic must not silently transpose a raw-contract price level onto another expiry or onto a continuous smart symbol. Exact future-retest tape is deferred to separately quoted/authorized Stage 2 when not already available.

## Live reproducibility

At each live session start:

1. refresh V0 and N0 mappings;
2. freeze the two raw IDs for that session;
3. subscribe to the unique raw candidate set;
4. maintain cumulative volume independently for each candidate;
5. at every decision, route using only volume from completed minutes preceding the decision;
6. never revise a historical routing decision using later trades.

## Side and causal policies unchanged

All previously frozen rules remain in force:

- native A/B/N retained;
- N never silently imputed in primary analysis;
- delta/CVD uncertainty bounds retained;
- PASSIVE_TOUCH cutoff strictly before contact-bar start;
- TOUCH_NEXT_OPEN through contact-bar close;
- ACCEPTANCE_RETEST through t0+5m under the frozen model;
- reclaim-based models through actual reclaim close, never later than t0+16m;
- post-entry 120m is outcome labeling, not predictor availability.

## Fixed sensitivity analyses

Every DEV_RANK1 report must show:

1. `DUAL_V0_N0_CAUSAL_ACTIVE` — primary;
2. `N0_FROZEN_ONLY` — sensitivity;
3. `V0_FROZEN_ONLY` — sensitivity.

Routing diagnostics such as selected candidate, V0/N0 cumulative-volume ratio, number of leader changes or distance to roll are QA variables. They cannot become unrestricted trading filters inside DEV_RANK1.

## Cost gate from metadata quote

Exact current candidate quote before the final pre-download re-quote:

- DUAL new acquisition: USD 20.825925588608;
- recommended hard cap: **USD 20.84**;
- paid pilot already observed: USD 4.01;
- projected cumulative project spend: USD 24.835925588608.

No market-data download is authorized by this document. The acquisition workflow must re-quote the exact frozen manifest immediately before download and stop if total cost exceeds USD 20.84.
