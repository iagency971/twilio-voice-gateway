# CHECKPOINT — COMEX native N1 complete / N2 Stage 1 quoted

Date: 2026-08-18
Branch: `agent/xau-comex-acquisition-plan`
Status: FROZEN AT N2 STAGE-1 FINANCIAL GATE

## Existing-POI path

The prior COMEX B1/B2-on-existing-XAU-POI path remains closed at DEV_RANK1. No DEV_RANK2, RETRO_CONFIRM or LOCKED_COMEX_TEST data have been opened.

This checkpoint concerns only the independent COMEX-native VWAP / POC / VAH / VAL hypothesis.

## N1 acquisition — complete

User authorization:

`OK NATIVE N1, plafond 0,45 $`

Frozen N1 quote before acquisition: 0.442661270503 USD.

N1 completion state:

- source sessions: 92;
- source levels: 368;
- N1 raw OHLCV-1m requests: 92 / 92 complete;
- records downloaded: 121,251;
- first run successes: 16;
- recovery successes: 76;
- confirmed successful-request cost upper bound: 0.442661270503 USD;
- conservative reserve for the prior 502 request: 0.004954114556 USD;
- conservative worst-case N1 total: 0.447615385059 USD;
- approved hard cap: 0.45 USD;
- hard cap respected: YES.

The recovery reused all 16 successful first-run files by SHA and did not replay them.

N2 was not downloaded during N1 acquisition.

## N1 native-level screen

Frozen primary native contact definition is unchanged:

- same raw source GC instrument;
- next eligible GC auction session only;
- exact frozen `contact_tick_price` on the GC 0.10 tick;
- contact requires an exact raw GC trade at that tick;
- M1 crossing never confirms contact.

N1 result over 368 source levels:

- 125 levels: no M1 bar in the next session can contain the exact contact tick under the frozen screen;
- 243 levels: at least one candidate M1 minute exists and exact raw tape is required;
- candidate level-minute rows: 9,093;
- unique candidate raw minutes: 8,725;
- fully merged one-shot N2 tape requests: 3,231.

## Full N2 quote — reference maximum only

A complete one-shot download of every candidate exact-tape interval was quoted metadata-only at:

**3.637339174767 USD**

No N2 market data were downloaded.

The full one-shot quote is not authorized and is retained only as a maximum reference.

## Sequential N2 acquisition frozen before any N2 outcome

Canonical freeze:

`COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md`

Mechanical rule:

1. For each of the 243 N2-required levels, sort N1 candidate minutes chronologically.
2. Stage 1 tests candidate rank 1 only.
3. Exact raw trades at the frozen tick resolve a level at its first such trade.
4. Levels without an exact tick trade advance mechanically to their next candidate rank.
5. Resolved levels never download later candidate ranks.
6. Identical candidate minutes are shared; only exactly contiguous candidate minutes on the same raw instrument/session may be merged.
7. No result-driven reordering, skipping or level selection is allowed.

## N2 Stage 1 frozen population

Deterministic from N1 only, before any N2 exact-tape outcome:

- levels: 243;
- first-candidate level rows: 243;
- unique first-candidate minutes: 222;
- merged raw `trades` requests: 214;
- one-minute requests: 206;
- two-minute requests: 8.

## N2 Stage 1 exact metadata quote

Stage 1 was quoted using `metadata.get_cost()` only:

**0.352496802811 USD**

State:

- `market_data_download_performed = false`;
- `n2_download_performed = false`;
- N2 Stage 1 download NOT AUTHORIZED;
- full N2 union download NOT AUTHORIZED;
- DEV_RANK2 / RETRO_CONFIRM / LOCKED_COMEX_TEST remain unopened.

## Next financial gate

Do not download N2 Stage 1 until explicit user authorization is recorded and cryptographically bound to the frozen Stage-1 manifest.

Recommended user authorization string if accepted:

`OK NATIVE N2 STAGE1, plafond 0,36 $`

The 0.36 USD cap gives a small safety margin over the exact 0.352496802811 USD metadata quote. Before any download, re-run a global exact-cost / record-count hard gate and stop if the current quote exceeds 0.36 USD.

After Stage 1 download:

1. detect exact tick trades only;
2. resolve first-contact levels;
3. mechanically construct Stage 2 only for unresolved levels;
4. quote Stage 2 metadata-only;
5. stop at the next financial gate.

## Canonical artifacts

- `xau-final-results/comex_dev_rank1_native_n1_acquisition_v1/ACQUISITION_COMPLETE.json`
- `xau-final-results/comex_dev_rank1_native_n1_acquisition_v1/acquisition_summary.json`
- `xau-final-results/comex_dev_rank1_native_n2_quote_v1/native_n2_quote.json`
- `xau-final-results/comex_dev_rank1_native_n2_quote_v1/native_n1_level_screen.csv`
- `xau-final-results/comex_dev_rank1_native_n2_quote_v1/native_n2_candidate_level_minutes.csv`
- `xau-final-results/comex_dev_rank1_native_n2_quote_v1/native_n2_market_request_manifest.csv`
- `xau-multiyear/docs/COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md`
- `xau-final-results/comex_dev_rank1_native_n2_stage1_quote_v1/native_n2_stage1_quote.json`
- `xau-final-results/comex_dev_rank1_native_n2_stage1_quote_v1/native_n2_stage1_level_manifest.csv`
- `xau-final-results/comex_dev_rank1_native_n2_stage1_quote_v1/native_n2_stage1_market_request_manifest.csv`
