# XAUUSD Z4 — Landmark Cadence DEV Sensitivity Results v0.1

**Status:** DEV COMPLETE — NO PRODUCTION CHANGE

Lookback fixed at **1,440 active M1**. Endpoint fixed at **REVISIT_240**.

| Cadence | BID ΔBrier all | BID weekly95 all | ASK ΔBrier all | ASK weekly95 all | BID ΔBrier common15 | ASK ΔBrier common15 | Dual-feed all | Dual-feed common15 |
|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 1 | 0.00162312 | [0.00065792, 0.00282852] | 0.00188916 | [0.00060895, 0.00395202] | 0.00149785 | 0.00177017 | PASS | PASS |
| 5 | 0.00160251 | [0.00056859, 0.00276648] | 0.00173926 | [0.00053365, 0.00350501] | 0.00160440 | 0.00166906 | PASS | PASS |
| 15 | 0.00147276 | [0.00069103, 0.00234559] | 0.00174284 | [0.00057578, 0.00344269] | 0.00147276 | 0.00174284 | PASS | PASS |

## Fold-by-fold BID ΔBrier — all cadence snapshots

| Cadence | APR | MAY | JUN | JUL |
|---:|---:|---:|---:|---:|
| 1 | 0.00118622 | 0.00137506 | 0.00149787 | 0.00241365 |
| 5 | 0.00077837 | 0.00143509 | 0.00121345 | 0.00292414 |
| 15 | 0.00129697 | 0.00157570 | 0.00184918 | 0.00120617 |

## Common-15 geometry/provenance

- BID: geometry hash parity = **FAIL**; hash `ad8dccf5fbb398d9af5934298bdec55f30a46eda117070cee6253e6334e65b34`.
- ASK: geometry hash parity = **FAIL**; hash `aba6186a2d64ce6ea6c2e441b48082132c06e6b3d2f297697e3222110524521a`.
- C15 exact pooled reproduction vs frozen DEV = **PASS**.

## Stability diagnostics

| Cadence | BID per-update drop | BID median lineage max age (active M1) | BID p95 lineage max age | BID common15 drop |
|---:|---:|---:|---:|---:|
| 1 | 0.015597 | 2.00 | 359.65 | 0.097814 |
| 5 | 0.035135 | 10.00 | 1005.00 | 0.080595 |
| 15 | 0.060491 | 30.00 | 1393.00 | 0.060491 |

## Preregistered result

- Provenance/geometry parity gate: **FAIL**.
- Shorter cadences eligible for targeted Pro review: **[]**.
- Decision-rule result: **NO_SHORTER_CADENCE_ELIGIBLE_RETAIN_C15**.
- C15 remains the validated incumbent until an explicit later decision.
- No Validation/OOS or production/Pine/R change is authorized by this DEV run.
