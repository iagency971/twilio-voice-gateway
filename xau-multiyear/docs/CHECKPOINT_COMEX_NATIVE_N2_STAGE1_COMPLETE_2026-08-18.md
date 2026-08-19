# CHECKPOINT — COMEX Native N2 Stage1 complete / Stage2 quoted

Date: 2026-08-18
Branch: `agent/xau-comex-acquisition-plan`

## Stage1 authorization and acquisition

User authorization: `OK NATIVE N2 STAGE1, plafond 0,36 $`.

Frozen Stage1 population before any N2 tape outcome:
- 243 levels;
- 222 unique first-candidate minutes;
- 214 merged raw `trades` requests;
- 206 one-minute requests + 8 two-minute requests;
- frozen/revalidated quote: 0.352496802811 USD.

Acquisition result:
- complete 214/214;
- 71,981 decoded raw trade rows;
- confirmed success cost upper bound 0.352496802811 USD;
- hard cap 0.36 USD respected;
- no later N2 stage downloaded;
- no full N2 union downloaded.

A first acquisition attempt stopped after the first paid request because an invalid QA assumed `metadata.get_record_count()` had to equal decoded trade rows on a one-minute request. The first raw file was preserved and reused without replay. Recovery used `get_record_count` only as metadata context, not an equality completeness assertion, and completed the remaining 213 requests under the original cap.

## Exact Stage1 contact resolution

Frozen contact rule remains:
> first chronological raw GC trade in the tested candidate minute whose price equals the frozen `contact_tick_price` exactly on the same raw source instrument.

Results across the 243 N2-required levels:
- exact contact resolved in Stage1: 231;
- Stage1 exact-contact rate: 95.0617283951%;
- unresolved after Stage1: 12;
- among those 12, exhausted with no remaining candidate minute: 5 => resolved no exact next-session contact;
- mechanically advancing to candidate rank 2: 7.

By level type:
- POC: 58 / 63 exact contacts in Stage1 = 92.0635%; 5 unresolved;
- VAH: 60 / 62 = 96.7742%; 2 unresolved;
- VAL: 56 / 59 = 94.9153%; 3 unresolved;
- VWAP: 57 / 59 = 96.6102%; 2 unresolved.

## Stage2 quote-only gate

Stage2 population is determined mechanically by the pre-outcome sequential freeze:
- Stage2 levels: 7;
- unique candidate-rank-2 minutes: 7;
- merged market requests: 7;
- exact metadata quote: 0.001557111741 USD.

Stage2 authorization state:
- market-data download: NOT AUTHORIZED;
- full N2 union: NOT AUTHORIZED;
- DEV_RANK2: NOT OPENED;
- RETRO_CONFIRM: NOT OPENED;
- LOCKED_COMEX_TEST: NOT OPENED.

Canonical Stage2 quote output:
`xau-final-results/comex_dev_rank1_native_n2_stage1_resolution_stage2_quote_v1/native_n2_stage1_resolution_stage2_quote.json`

Stage2 market request manifest SHA-256:
`46597c127a09c0b05a59e01114759c30585db1a978ecb75d2098958266cd6fca`

Stage2 level manifest SHA-256:
`23f27d7c5861d1fba7889d1149423aac0aea3f0f1a5fd2fa757b65479b64f2cb`

## Next allowed action

Stop for explicit user authorization before any Stage2 raw `trades` download.
