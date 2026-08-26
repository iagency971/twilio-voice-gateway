# XAUUSD Z4 / E-BUY — C1 minute-refresh preregistration Addendum B: DEV stability gate

**Frozen:** 2026-08-26 while the dedicated C1/C5 DEV reconstruction jobs are still running and before the E-BUY metric step has started or any new C1 E-BUY result has been inspected.

**Purpose:** make `stability/churn remains operationally acceptable` from the C1 preregistration non-post-hoc for the preliminary Jan-Jul 2024 outcome-blind location gate.

## 1. Scope

This addendum is location/outcome-blind only. It does not inspect or gate any reaction, TP1, invalidation, MFE/MAE, E-score or profitability result.

The preliminary DEV window is Jan-Jul 2024 because exact frozen BID/ASK source hashes and pre-existing C1/C5 detector evidence are available there. Passing this preliminary gate authorizes the already-preregistered retrospective H1/H2 C1 reaction comparison; it does not promote C1.

## 2. Reuse of pre-existing E-BUY absolute gates

No C1-specific coverage threshold is optimized. For **both BID and ASK**, C1 must satisfy the same absolute E-BUY location gates that were frozen before this C1 study:

- coverage within `1.0v >= 0.80`;
- coverage within `1.5v >= 0.90`;
- coverage within `2.0v >= 0.95`;
- displayed-zone count median between `1` and `3`;
- displayed-zone count p90 `<= 3`;
- nearest-zone distance p90 `<= 1.5v`;
- survival-aware display persistence `>= 0.70`;
- unexplained disappearance share among survival-eligible zones `<= 0.05`.

These are the existing E-BUY gates, not thresholds selected from C1 results.

## 3. Detector provenance gate

At common C1/C5 detector timestamps:

- identical zone count;
- identical side;
- center absolute error `<= 1e-12 USD`;
- zlo/zhi absolute error `<= 1e-8 USD`.

Any failure is `PROVENANCE_FAIL` and blocks interpretation.

## 4. Churn diagnostics

The following are mandatory reports but are **not given new hard numerical cutoffs in this DEV gate**, because no pre-existing E-BUY operational threshold exists for them and inventing one now would be arbitrary:

- native display-episode lifetime in active minutes;
- slot-rank change share;
- nearest/top1 material-change share;
- matched center/zlo/zhi drift in v units;
- common-5-minute C1/C5 top1 agreement and top3 Jaccard;
- runtime C1/C5 ratio.

They must be interpreted explicitly against C5 before reaction work is authorized. A later Pine feasibility gate may reject C1 for engineering/runtime reasons even if this DEV location gate passes.

The v1.0 derived `births_per_100_transitions` metric is excluded from interpretation because its numerator includes non-contiguous sequence/session starts while its denominator contains only contiguous transitions. v1.1 suppresses that invalid derived rate. Raw episode counts and all geometry/matching metrics are unaffected.

## 5. Preliminary authorization rule

`C1_REFRESH_DEV_LOCATION_GATE_PASS` requires all of:

1. BID detector provenance pass;
2. ASK detector provenance pass;
3. all eight absolute C1 E-BUY gates in Section 2 pass on BID;
4. all eight absolute C1 E-BUY gates in Section 2 pass on ASK;
5. no future reaction outcome consumed by the runner.

If this fails, retain C5 and do not run H1/H2 C1 reaction comparison without a new preregistration.

If this passes, C1 is only `AUTHORIZED_FOR_PREREGISTERED_RETROSPECTIVE_REACTION_COMPARISON`; no production or Pine promotion follows.
