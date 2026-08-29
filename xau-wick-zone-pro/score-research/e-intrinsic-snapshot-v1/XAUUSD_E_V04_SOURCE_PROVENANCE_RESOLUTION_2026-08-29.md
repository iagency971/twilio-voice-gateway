# XAUUSD E v0.4 source — outcome-blind hash provenance resolution

**Date:** 2026-08-29  
**Scope:** source integrity only; no reaction/trading outcomes inspected.

The frozen v0.4 manifest records candidate SHA-256:

`dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920`

The tracked file is:

`xau-wick-zone-pro/entry-research/ebuy-coverage-v0-4/XAUUSD_Z4_EBUY_STICKY_CANDIDATES_v0_4.csv.gz`

A first V1 guard incorrectly compared the legacy manifest SHA against the gzip **container bytes** and blocked the run. An outcome-blind provenance-only GitHub Actions check then hashed distinct representations before any real ledger QA was allowed.

Observed representations:

- gzip binary size: `950353` bytes;
- gzip binary SHA-256: `1a6fc6451b80d7b57a7ce37d005586b59ccf94235d11fc32486a6b9dca7f4a3c`;
- decompressed CSV size: `4028000` bytes;
- decompressed CSV SHA-256: `dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920`;
- normalized-LF CSV SHA-256: `dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920`;
- CSV data rows: `27636`;
- header: `time,close,v60,upper_z4_count,nearest_upper_z4_dist_v,entry_rank,family,center,zlo,zhi,distance_v`.

Therefore the legacy v0.4 manifest hash is confirmed to refer to the **decompressed CSV payload**, not to the gzip transport/container representation.

## Frozen V1 rule

V1 records and verifies both hashes:

1. the gzip binary SHA for exact artifact/container reproducibility;
2. the decompressed payload SHA for parity with the legacy v0.4 manifest.

The legacy expected value `dee5…` is checked against the decompressed payload. This is a representation clarification, not a data substitution or methodological change.

No outcome was opened during this resolution. The source candidate contents used by V1 are exactly those whose decompressed payload matches the v0.4 frozen manifest.
