# COMEX DEV_RANK1 — Native N2 sequential exact-tape acquisition freeze v1

Date: 2026-08-18
Branch: `agent/xau-comex-acquisition-plan`
Status: FROZEN BEFORE ANY N2 MARKET-DATA DOWNLOAD

## Purpose

Reduce exact-tape acquisition cost without changing the preregistered native-contact definition.

N1 is complete. Its OHLCV-1m screen is outcome-free with respect to N2 exact trades and has produced:

- 368 frozen source levels (VWAP / POC / VAH / VAL);
- 125 levels with no M1 bar capable of containing the exact contact tick in the next eligible auction session;
- 243 levels requiring exact raw-tape confirmation;
- 9,093 level-minute candidate rows;
- 8,725 unique candidate minutes;
- 3,231 merged candidate-tape requests for a full one-shot N2 maximum quote of 3.637339174767 USD.

No N2 trades have been downloaded.

## Contact definition remains unchanged

For each frozen source level:

1. use the same raw GC `source_instrument_id` that created the level;
2. use only the already-frozen next eligible GC auction session;
3. the contact price is the frozen `contact_tick_price` on the valid GC 0.10 tick;
4. primary contact is the first chronological raw GC trade whose price equals `contact_tick_price` exactly;
5. M1 high/low crossing is never a contact confirmation.

## Sequential N2 rule

For every one of the 243 N2-required levels:

1. Sort its N1 candidate minutes chronologically.
2. Candidate rank 1 is the earliest M1 minute whose low/high span includes the frozen contact tick.
3. N2 Stage 1 contains candidate rank 1 for every unresolved level.
4. After exact raw trades for a stage are acquired, a level is RESOLVED_CONTACT if any trade in its tested candidate minute equals the contact tick exactly. Its contact time is the first such trade timestamp.
5. A level with no exact tick trade in the tested candidate minute remains UNRESOLVED and advances mechanically to its next candidate rank.
6. Stage k contains candidate rank k only for levels still unresolved after stages 1..k-1.
7. A level with no remaining candidate minute after all prior candidates have been tested is RESOLVED_NO_CONTACT for the next-session primary test.

No candidate minute may be skipped because of its price path, cost, level type, year, direction, family, or any result observed in earlier levels.

## Deduplication / merging rule

Within each stage only:

- identical candidate minutes shared by multiple unresolved levels are downloaded once;
- exactly contiguous candidate minutes on the same raw instrument and same next-session date may be merged into one `trades` request;
- no noncandidate minute may be added merely to reduce request count;
- one downloaded raw interval may resolve multiple levels if their frozen contact ticks are traded inside that interval.

## Stage 1 population frozen before N2 outcomes

From the N1 candidate manifest:

- levels entering Stage 1: 243;
- first-candidate level rows: 243;
- unique first-candidate raw minutes after sharing: 222;
- merged Stage-1 raw `trades` intervals: 214;
- 206 intervals are one minute and 8 intervals are two exactly contiguous candidate minutes.

These counts are deterministic from N1 only and are frozen before any N2 trades download.

## Financial gate

The full one-shot N2 quote is a maximum reference, not an authorization.

Before any N2 Stage 1 download:

1. construct and hash the Stage-1 manifest;
2. obtain `metadata.get_cost()` only;
3. publish `n2_download_performed=false`;
4. stop for explicit user financial authorization.

Every later stage requires a new manifest built mechanically from unresolved levels, a metadata-only cost quote, and a new financial gate before market-data download.

## Prohibited changes

After N2 outcomes begin, do not:

- reorder or skip candidate minutes;
- change the exact contact tick;
- substitute continuous GC for the source raw instrument;
- call an M1 crossing a contact;
- choose levels/types/years based on prior N2 results;
- download later candidate ranks for a resolved level;
- change the next-session definition;
- open DEV_RANK2, RETRO_CONFIRM, or LOCKED_COMEX_TEST as a rescue path.

## Current authorization state

- N1: complete under the approved 0.45 USD cap.
- N2 Stage 1: NOT AUTHORIZED for download.
- N2 full union: NOT AUTHORIZED for download.
- DEV_RANK2 / RETRO_CONFIRM / LOCKED_COMEX_TEST: NOT OPENED / NOT AUTHORIZED.
