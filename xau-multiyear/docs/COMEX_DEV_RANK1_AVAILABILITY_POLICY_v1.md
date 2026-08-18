# COMEX DEV_RANK1 — Session availability and data-quality policy v1

Date: 2026-08-18
Status: frozen before paid DEV_RANK1 acquisition.

## Principle

A deterministically selected XAU research date is **not replaced merely because GC is closed, holiday-shortened, sparse, or technically imperfect**. Replacing such dates after inspecting COMEX availability would bias the sample toward liquid/easy days.

## Status classes

Each selected session receives one or more non-alpha QA statuses:

- `GC_CLOSED`: no GC.FUT parent trades in the canonical auction interval;
- `GC_SHORT_OR_HOLIDAY`: legitimate market activity exists but the canonical session is materially shortened/sparse;
- `GC_COVERAGE_SUSPECT`: tape or OHLCV coverage is internally inconsistent or unexpectedly incomplete;
- `GC_ROLL_DIVERGENCE`: causal V0 and N0 mappings point to different contracts at session start;
- `GC_OK`: no material availability issue detected.

These statuses are used for missingness/QA and sensitivity reporting. They are not freely optimized trading features.

## Missing data handling

- A `GC_CLOSED` session remains an independent selected date. COMEX flow/profile features are missing; the XAU baseline remains evaluable.
- A legitimate short/holiday session is retained with its actual data. It is never stretched to synthetic full-session volume.
- If exact selected-session OHLCV is incomplete but raw trades are available, selected-session M1 OHLCV may be reconstructed deterministically from the raw trades for that same frozen contract.
- Continuous-context gaps outside acquired full sessions remain missing/stale flags and are not forward-filled across session or contract boundaries.
- A coverage-suspect feature group is excluded only for the affected session/window, with an explicit missingness flag.

## Known pre-acquisition examples

- 2011-12-26: GC.v0/raw/GC.FUT all zero — closed/no GC records, retain as selected date with COMEX missing.
- 2014-01-20: same — retain with COMEX missing.
- 2012-11-22: extremely short/sparse GC activity, retain as holiday-type observation.
- 2014-06-13: very sparse whole-family GC coverage; retain and flag coverage/sparse condition.
- 2015-02-05: normal trade tape but severely incomplete OHLCV-1m for the selected mapping; reconstruct selected-session M1 from raw trades if this contract is selected.
- Roll-transition dates are handled by the separately frozen contract-selection rule, not by dropping the date.

## Selection integrity

No selected session may be replaced, added, or removed because its COMEX features or eventual XAU outcomes are favorable or unfavorable. Only structural panel corrections already frozen before COMEX outcomes (weekend removal; replacement of exposed confirm/test pilot dates in the same stratum) are permitted.
