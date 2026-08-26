# XAUUSD Z4 C1 Refresh E-BUY — Addendum K: exact Fenwick-prefix accelerator

Date: 2026-08-26
Status: OUTCOME-BLIND COMPUTATIONAL ADDENDUM

## Purpose

The exact local-grid accelerator in Addendum J is mathematically identical to the frozen C1 detector but its first implementation still computed the local prefix by summing `d[:ilo]` at every C1 landmark. On the 0.01 USD global grid this retains an unnecessary O(N_grid) operation.

This addendum authorizes a purely computational replacement of that prefix operation by a Fenwick tree (binary indexed tree), while preserving every detector input, update, future guard, grid coordinate, local slice, smoothing operation, peak operation and zone boundary computation.

## Frozen equivalence

For each of `dL`, `dB`, and `dU`:

1. Every original difference-array point update is applied unchanged to the original dense difference array.
2. The same signed point update is also applied to a Fenwick tree.
3. At a landmark, the count at the first local level is reconstructed as:
   `prefix(ilo - 1) + cumsum(d[ilo:ihi+1])`.
4. The Fenwick prefix is exactly the integer sum of `d[0:ilo]`; no approximation, interpolation or float computation is permitted.
5. `zone_detect` receives exactly the same integer vector as the frozen full-grid detector would have supplied for `wick[ilo:ihi+1]`.
6. Global level indices used for center/zlo/zhi and exposure metrics are restored by the same `ilo` offset.
7. The historical future guard `i + HORIZON + REACT_MAX >= N` remains unchanged.
8. Outcomes are not computed by the accelerator; only `time, side, center, zlo, zhi` are emitted.

## Mandatory parity gate

Before February or March 2026 output may be consumed, exact geometry parity must pass against the already-computed frozen full detector on BOTH:

- 2025-10
- 2026-04

Required parity:

- identical row count;
- identical timestamp ordering after canonical sort;
- identical side;
- center max absolute error <= 1e-12 USD;
- zlo max absolute error <= 1e-8 USD;
- zhi max absolute error <= 1e-8 USD.

Any failure invalidates this accelerator. No reaction outcome may be opened using a failed accelerator.

## Scientific authorization

NONE. This addendum changes computation cost only. It cannot change model selection, thresholds, zones, reactions, statistics, or production behavior.
