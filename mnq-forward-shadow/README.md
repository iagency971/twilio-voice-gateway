# MNQ 12-Model Prospective Shadow

This directory contains the prospective shadow-only forward harness frozen from 2026-08-21 onward.

- Market data: Yahoo `NQ=F` 1-minute, zero-cost proxy only.
- Strategy: pinned external 12-model commit `d472d6b442764c2adafbba4bbeb96881c100e3e0`.
- Validation status: proxy only. Any pass requires official-CME remeasurement before live use.
- Paid market data: prohibited in this shadow harness.

The intended daily execution time is after the US cash session is complete. Results are appended to `mnq-forward-shadow/results/ledger.csv` and summarized in `SUMMARY.json`.
