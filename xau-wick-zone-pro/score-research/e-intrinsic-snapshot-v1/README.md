# E intrinsic snapshot V1

Outcome-blind infrastructure for the XAUUSD M1 BUY US E-zone score research.

## Canonical input

`xau-wick-zone-pro/entry-research/ebuy-coverage-v0-4/XAUUSD_Z4_EBUY_STICKY_CANDIDATES_v0_4.csv.gz`

Expected SHA-256: `dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920`.

## Commands

```bash
python xau_e_intrinsic_snapshot_v1.py \
  --candidates <v0.4.csv.gz> \
  --output E_INTRINSIC_SNAPSHOT_V1_LEDGER.csv.gz \
  --manifest E_INTRINSIC_SNAPSHOT_V1_MANIFEST.json \
  --expected-source-sha256 dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920

python xau_e_intrinsic_snapshot_qa_v1.py \
  --candidates <v0.4.csv.gz> \
  --ledger E_INTRINSIC_SNAPSHOT_V1_LEDGER.csv.gz \
  --manifest E_INTRINSIC_SNAPSHOT_V1_MANIFEST.json \
  --output E_INTRINSIC_SNAPSHOT_V1_QA.json \
  --expected-source-sha256 dee5bfdd1ed6bb0b7eebc19280cb3cb3ee2e35c3da14a14d3ee1ee644a52a920
```

`test_xau_e_intrinsic_snapshot_v1.py` uses synthetic data only and never opens project outcomes.
