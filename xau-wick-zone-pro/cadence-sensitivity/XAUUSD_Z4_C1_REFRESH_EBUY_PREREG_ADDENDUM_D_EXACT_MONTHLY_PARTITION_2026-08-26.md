# Addendum D — Exact monthly computational partition of mechanical C1/C5 detectors

**Frozen:** 2026-08-26, before any C1 H1/H2 reaction result is generated or inspected.

**Scope:** computational partition only. No detector, location, contact, trigger, target, invalidation, score, or decision rule changes.

## 1. Motivation

The frozen mechanical C1 detector is substantially more expensive than C5 over the continuous 24-month OOS chronology. The monolithic computation is not scientifically required if the target-month geometry can be reproduced exactly from bounded source context.

The detector itself remains the frozen mechanical source mutation defined in the parent preregistration:
- C1 patched SHA-256 `86a5b1af2e77d0e78526652c03f4c6f1a6bfbdaaf92d21e34c1b121f6fdf4dcb`;
- C5 patched SHA-256 `7bb47cfc78a26dd7a74965556352114a8e31ca1545ef4d21a987951daf417d24`;
- all other source mutations = 0.

## 2. Exact target-month source context

The research detector has both:
- a finite backward `LOOKBACK` dependency; and
- an end-of-file future-horizon guard in the frozen source.

Therefore exact monthly partitioning must provide both backward and forward file context where those months exist.

For target month `M`:
- `2024-08`: use `M + next(M)`; there is no pre-study previous month, preserving the continuous study start exactly;
- interior months `2024-09` through `2026-06`: use `prev(M) + M + next(M)`;
- `2026-07`: use `prev(M) + M`; there is no post-study next month, preserving the continuous study end/tail guard exactly.

Run the unchanged frozen cadence detector on that source context and retain only detector rows whose `time` lies inside target month `M`.

## 3. Assembly

After all 24 target months are generated independently:
- concatenate them in chronological order;
- sort by `time, side, center`;
- do not alter geometry values;
- use the assembled C1/C5 geometry as the continuous 2024-08 through 2026-07 detector stream for downstream E-BUY state construction.

## 4. Mandatory equivalence gate

The existing common-anchor C1/C5 detector geometry parity remains mandatory.

In addition, this partition is considered only a compute optimization. If any available monolithic reference is compared, target-month geometry must be identical at shared timestamps; no scientific interpretation may be based on a partition mismatch.

## 5. Outcome status

No C1 H1/H2 reaction result had been generated or inspected when this addendum was frozen. This addendum authorizes no Pine or production change.