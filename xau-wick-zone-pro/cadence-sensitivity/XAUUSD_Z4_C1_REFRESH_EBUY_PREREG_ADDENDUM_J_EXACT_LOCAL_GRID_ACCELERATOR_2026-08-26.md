# XAUUSD Z4 / E-BUY — C1 refresh preregistration Addendum J: exact local-grid accelerator

**Frozen:** 2026-08-26, before any valid H1/H2 C1 reaction outcome is opened or interpreted.  
**Scope:** computational optimization of the Addendum-G geometry projection only; no scientific geometry or reaction rule change.

## Observation

The frozen Z4 detector stores wick/body exposure as global difference arrays on the fixed absolute $0.01 grid. At each eligible state it currently materializes cumulative counts over the entire global price grid, then immediately restricts zone detection to the rolling `rlo/rhi` band `[ilo:ihi]`.

For a difference array `d`, the exact exposure count at global level `k` is `sum(d[0:k+1])`. Therefore the exact vector on `[ilo:ihi]` can be computed without materializing levels outside that interval as:

`offset = sum(d[:ilo])`

`local = offset + cumsum(d[ilo:ihi+1])`

All quantities are integer counts; no approximation is introduced.

## Authorized optimization

Starting from the exact Addendum-G C1 geometry projection:

- keep the fixed absolute grid origin `base=0.0`, `STEP=.01`, all difference-array updates, lookback, cadence, future-file guard, rolling range, smoothing, peaks, prominence, peak-width boundaries, and side classification unchanged;
- materialize `cntL/cntB/cntU` only for global levels `[ilo:ihi]` using the exact offset-plus-local-cumsum identity above;
- pass the same local wick vector to `zone_detect`, while preserving the original global grid indices via an explicit global offset;
- convert center, zlo, zhi and all zone-level exposure lookups back to the identical global indices before recording rows;
- retain only `time/side/center/zlo/zhi` and stop before unused outcome/lineage work, as already authorized by Addendum G.

## Mandatory parity gate

The local-grid accelerator is admissible only if it reproduces the already-completed full frozen C1 detector on both:

- `2025-10`, and
- `2026-04`,

using the same `previous + target + next` monthly context, with:

- identical target-month row count and timestamp set;
- identical zone count at each timestamp;
- identical side;
- center max absolute error <= `1e-12 USD`;
- zlo/zhi max absolute error <= `1e-8 USD`.

The comparison must be against the original full-detector artifacts from run `33009725953`, not against another accelerator.

## Use

Only after both parity checks pass may local-grid outputs substitute for still-missing full-detector C1 shards (`2026-02`, `2026-03`; or `2026-01` only if the full artifact were unavailable). Full detector remains preferred whenever available.

The final C1-vs-C5 common-anchor geometry parity remains mandatory after all monthly pieces are assembled.

**Authorization:** computation-only fallback. No reaction outcome, statistical decision, Pine change, or production promotion is authorized.