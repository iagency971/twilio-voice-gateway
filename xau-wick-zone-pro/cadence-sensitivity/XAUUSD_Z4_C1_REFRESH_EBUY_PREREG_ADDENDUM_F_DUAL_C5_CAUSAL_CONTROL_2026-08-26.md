# Addendum F — Dual C5 causal control: historical bridge + mechanically matched cadence isolate

**Frozen:** 2026-08-26, before any valid C1 H1/H2 reaction result is generated or inspected.

## 1. Outcome-blind geometry discrepancy discovered

An early partition QA compared October 2024 mechanical C5 geometry (base-0 frozen detector, cadence=5) against the historical shifted-grid source-faithful monthly reaction geometry.

Observed before any C1 reaction outcome:
- mechanical C5 rows: `34,176`;
- source-faithful shifted-grid rows: `34,175`;
- exactly one timestamp had a row-count difference: `2024-10-04T12:55:00Z`;
- the extra mechanical row was a lower zone centered at `2633.11`;
- all other rows/timestamps on that month matched within sub-picodollar floating tolerance.

The prior shifted-grid semantic-parity certificate was valid on its tested sample but did not establish absolute identity over all 24 OOS months.

This is a geometry/provenance finding, not a reaction result.

## 2. Why one C5 control is insufficient

Two different scientific questions must be kept separate:

1. **Historical bridge:** does the new causal timing/state machinery remain connected to the exact C5 evidence actually used by the frozen E-BUY historical pipeline?
2. **Cadence isolate:** what changes when the exact same canonical Z4/E-BUY detector architecture is refreshed at 1 minute instead of 5 minutes?

Using only shifted-grid historical C5 for question 2 can allow rare grid-origin differences to contaminate a cadence effect. Using only mechanically matched C5 loses the exact bridge to the historical frozen evidence.

## 3. Frozen dual-control design

The causal study must therefore report both C5 controls.

### A. `C5_SOURCE_FAITHFUL_CAUSAL`
- displayed E-BUY zones from the exact frozen OOS candidate table;
- target geometry from the source-faithful monthly shifted-grid H1/H2 geometry;
- symmetric `CAUSAL_ACTIVE_INTERVAL_V1` timing;
- Addendum-B sequential episode-state propagation;
- frozen historical baseline remains separately consumed as provenance.

Purpose: bridge to the exact historical research lineage.

### B. `C5_MECHANICAL_MATCHED_CAUSAL`
- Z4 detector = same frozen base-0 canonical source as C1;
- cadence literal = 5 minutes;
- continuous Aug-2024 through Jul-2026 construction;
- E-BUY architecture rebuilt with the same frozen `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`, top-3, local band, de-duplication and C5 warm-up already frozen;
- target geometry from the same mechanical C5 detector state;
- same causal timing and sequential episode-state semantics as C1.

Purpose: primary clean isolation of cadence, because the only scientific detector change between this C5 and C1 is the frozen cadence literal.

### C. `C1_MECHANICAL_CAUSAL`
- unchanged parent-preregistered C1 detector and E-BUY architecture;
- same continuous state, timing, episode-state and common-support rules.

## 4. Geometry discrepancy audit

Before interpreting reaction outcomes, report over H1 and H2:
- mechanical-C5 vs source-faithful-C5 row counts;
- number/share of timestamps with row-count mismatch;
- mismatches split by lower/upper side where identifiable;
- common-row center/zlo/zhi max absolute errors;
- whether the nearest upper target differs on any causal E-BUY contact opportunity, if evaluated without using reaction outcomes.

No mismatch is silently discarded.

## 5. Primary cadence effect

The primary cadence-effect estimate is:

`C1_MECHANICAL_CAUSAL - C5_MECHANICAL_MATCHED_CAUSAL`.

The source-faithful comparison is reported as a robustness/historical-bridge estimate:

`C1_MECHANICAL_CAUSAL - C5_SOURCE_FAITHFUL_CAUSAL`.

A C1 cadence claim is not accepted if its direction materially depends on which C5 control is used, or if rare geometry differences explain the apparent gain.

All comparisons continue to use the common complete-session support frozen in Addendum E.

## 6. Historical baseline and nonclaims

The full historical C5 H1/H2 anchors remain unchanged and consumed with provenance guards. This addendum does not rewrite them.

No production/Pine promotion is authorized. No E-score transfer, refit, or recalibration is authorized.