# CHECKPOINT — COMEX native exact-contact classification complete

Date: 2026-08-19
Branch: `agent/xau-comex-acquisition-plan`
Status: N1 + sequential N2 exact-contact phase COMPLETE

## Scope

This checkpoint closes only the exact-contact question for the frozen COMEX DEV_RANK1 native VWAP / POC / VAH / VAL levels.
It does **not** claim a reaction edge, profitability edge, or promotion to DEV_RANK2.

Existing-POI COMEX B1/B2 remains closed as NO_GO for DEV_RANK2. The native COMEX zone hypothesis is separate.

## Frozen population

- source sessions with valid raw GC source: 92
- native source levels: 368
- level types: 92 POC / 92 VAH / 92 VAL / 92 VWAP
- contact price: frozen valid GC 0.10 tick
- primary horizon: frozen next eligible GC auction session only
- raw instrument: same source `source_instrument_id`; no continuous-contract or CFD substitute
- contact definition: first chronological raw GC trade exactly equal to frozen `contact_tick_price`

## N1 screen

N1 `ohlcv-1m` acquisition was completed under the separately approved 0.45 USD cap.

- 368 source levels
- 125 `NO_EXACT_CONTACT_N1_SCREEN`
- 243 levels required exact N2 tape

N1 confirmed-success cost upper bound: 0.442661270503 USD.
Possible prior failed-attempt reserve from the original N1 502: 0.004954114556 USD.
Conservative N1 worst-case total: 0.447615385059 USD.

## Sequential N2 acquisition

The sequential N2 protocol was frozen before any N2 exact-trade outcome:

1. test candidate rank 1 for all 243 N2-required levels;
2. advance only unresolved levels to candidate rank 2;
3. advance only unresolved levels to candidate rank 3;
4. stop immediately once exact contact is found;
5. if all candidate minutes are exhausted with no exact trade, classify no-contact;
6. every paid stage requires a fresh metadata-only quote and explicit financial authorization.

Frozen protocol: `COMEX_DEV_RANK1_NATIVE_N2_SEQUENTIAL_ACQUISITION_FREEZE_v1.md`.

### Stage 1

User authorization: `OK NATIVE N2 STAGE1, plafond 0,36 $`

- levels: 243
- merged market requests: 214
- exact cost upper bound: 0.352496802811 USD
- exact contacts resolved at Stage 1: 231
- Stage-1 exhausted no-contact: 5
- advanced to Stage 2: 7

A false post-download QA failure on the first request was traced to misuse of Databento `metadata.get_record_count()` for 1–2 minute windows. The first paid raw file was salvaged and not replayed. Final Stage-1 acquisition: 214/214 complete.

### Stage 2

User authorization: `OK NATIVE N2 STAGE2, plafond 0,002 $`

- levels: 7
- requests: 7
- exact cost upper bound: 0.001557111741 USD
- decoded trade records: 216
- exact contacts resolved at Stage 2: 6
- advanced to Stage 3: 1

### Stage 3

User authorization: `OK NATIVE N2 STAGE3, plafond 0,025 $`

Frozen final case:

- level id: `1223ab410b28e74ebbed372e`
- source research date: 2012-09-06
- next eligible session: 2012-09-07
- source instrument id: `118951`
- level type: VAL
- contact tick: 1702.0
- final candidate rank: 3 of 3
- candidate minute: 2012-09-07 12:30:00–12:31:00 UTC

Pre-download hard gate:

- frozen quote: 0.024528264999 USD
- immediate current exact quote: 0.024528264999 USD
- approved cap: 0.025 USD
- remaining margin: 0.000471735001 USD

Run: `32251356108`
Conclusion: SUCCESS

Acquisition:

- requests: 1/1
- decoded trade records: 4,694
- exact cost upper bound: 0.024528264999 USD
- hard cap respected: true

Final Stage-3 result:

- exact tick trade count at 1702.0: 7
- first exact contact: 2012-09-07T12:30:00.554000+00:00
- final resolution: `RESOLVED_CONTACT_STAGE3`
- no Stage 4 exists for this level because candidate rank 3 was the final frozen candidate.

## Final exact-contact classification — 368/368

All 368 native levels are now classified.

- exact contacts: 238
- resolved no-contact: 130
- unresolved: 0
- exact-contact rate: 238 / 368 = 64.67391304347826%

By level type:

| Level type | Levels | Exact contacts | No contact | Exact-contact rate |
|---|---:|---:|---:|---:|
| POC | 92 | 62 | 30 | 67.3913043478% |
| VAH | 92 | 61 | 31 | 66.3043478261% |
| VAL | 92 | 58 | 34 | 63.0434782609% |
| VWAP | 92 | 57 | 35 | 61.9565217391% |

Canonical final files:

- `xau-final-results/comex_dev_rank1_native_n2_final_contact_classification_v1/native_n2_final_contact_classification.json`
- `xau-final-results/comex_dev_rank1_native_n2_final_contact_classification_v1/native_n2_stage3_resolution.csv`
- `xau-final-results/comex_dev_rank1_native_n2_final_contact_classification_v1/native_368_contact_status_final.csv`
- `xau-final-results/comex_dev_rank1_native_n2_final_contact_classification_v1/native_368_contact_status_by_type_final.csv`

Canonical SHA-256 values from final manifest:

- final 368 status: `8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a`
- final by-type status: `f7bec939057e5e554743603371de63cdcd592d086bd9d668dc8a9427484dd1f7`
- Stage-3 resolution: `0c1ad21192c8eaf9c73dda860662d7cb10a4f79c81e38a01b4b11d5ae712258d`

## Cost accounting

N2 sequential exact-tape confirmed-success cost upper bound:

- Stage 1: 0.352496802811 USD
- Stage 2: 0.001557111741 USD
- Stage 3: 0.024528264999 USD
- total N2: 0.378582179551 USD

Including N1:

- confirmed-success N1 + N2 upper bound: 0.821243450054 USD
- conservative total including the possible prior failed N1-attempt reserve: 0.826197564610 USD

No additional market-data acquisition is authorized by this checkpoint.

## Scientific interpretation boundary

The 64.67% figure is a **contact incidence**, not a win rate and not evidence of an edge.
It answers only: within the frozen next eligible auction session, did raw GC actually trade the native COMEX level exactly?

The next scientific question is separate:

> Conditional on exact native COMEX contact, what is the subsequent price reaction, its direction, magnitude, adverse excursion, timing, persistence, and dependence on level type / context?

The reaction protocol must be frozen before looking at reaction outcomes or optimizing thresholds.

## Locked-state preservation

- DEV_RANK2 opened: false
- RETRO_CONFIRM opened: false
- LOCKED_COMEX_TEST opened: false
- full one-shot N2 union downloaded: false
- Stage 4: not applicable / does not exist for the last unresolved level

No promotion or paid extension is authorized by this checkpoint.
