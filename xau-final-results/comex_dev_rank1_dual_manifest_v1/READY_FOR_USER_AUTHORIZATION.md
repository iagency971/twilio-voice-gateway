# DEV_RANK1 DUAL — Ready for explicit user authorization

Date: 2026-08-18
Status: **NO DEV_RANK1 MARKET-DATA DOWNLOAD AUTHORIZED**.

## Canonical architecture

`DUAL_V0_N0_CAUSAL_ACTIVE`

Controlling roll policy:

`xau-multiyear/docs/COMEX_DEV_RANK1_ROLL_POLICY_CANONICAL_v2.md`

## Frozen acquisition manifest

- analytical sessions: 96
- V0/N0 divergent session-start mappings: 10
- new raw `trades` requests: 102
  - N0 primary candidate raw requests: 93
  - additional V0 dual-alternate raw requests: 9
- continuous context requests: 1 (`GC.n.0 / ohlcv-1m`, 2010-06-06 to 2019-01-01)
- total new requests: 103
- frozen request CSV SHA-256: `25b1cfbd33215f8a1d7a9d6ac86515777df382d5be4fa4f4a74ebb541b381794`

Controlling current metadata quote: USD 20.825925588608.
Hard cap: **USD 20.84**.
Paid pilot already observed: USD 4.01.

## Dormant one-shot acquisition workflow

`.github/workflows/xau-comex-dev-rank1-dual-acquire.yml`

The workflow triggers only on:

`xau-authorizations/DEV_RANK1_DUAL_20_84.json`

That authorization file is intentionally absent until explicit user approval.

The workflow will:

1. verify exact authorization text and request-CSV SHA;
2. refuse execution if a completion marker already exists;
3. re-quote all 103 requests with Databento metadata immediately before any market-data call;
4. abort the whole acquisition if the exact current total exceeds USD 20.84;
5. re-check each request immediately before its sole paid `get_range` call;
6. make no automatic retry of paid range requests;
7. skip any zero-record request without making a market-data range call;
8. download at most four requests concurrently;
9. hash and preserve each DBN output as a separate GitHub Actions artifact;
10. create `ACQUISITION_COMPLETE.json` only if every one of the 103 request markers is present.

A partial failure must not be recovered by re-running the whole acquisition. Any recovery is to be separately authorized only for missing request IDs.

## Exact user authorization required

`OK DEV_RANK1 DUAL, plafond 20,84 $`

Only after that explicit message may `xau-authorizations/DEV_RANK1_DUAL_20_84.json` be created from the frozen template.
