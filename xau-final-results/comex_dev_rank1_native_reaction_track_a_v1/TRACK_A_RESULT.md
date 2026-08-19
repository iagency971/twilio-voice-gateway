# COMEX DEV_RANK1 native reaction — Track A result

Date: 2026-08-19

## Frozen binding

- pre-outcome manifest SHA-256: `60713b922eefe24dd8fbc306c1f26cc2557c829ccd0080649afbc9071972ca47`
- artifact freeze commit: `93930f82c3168dfd02a05edc57b78811739db9eb`
- frozen matching re-generated before outcomes and exact-identity checked: **PASS**
- new market-data API/download/spend: **NONE**

## Primary preregistered result

- matched events: **227**
- matched treated dates: **81**
- W15 `theta_NRB15`: **-0.0177850348991**
- 95% date-cluster bootstrap CI: **[-0.0389945778026, 0.00121197068573]**
- date-weighted raw reaction-balance difference: **-3.62119341564 GC ticks**
- 50,000-draw two-sided sign-flip p: **0.0823583528329**

## Frozen gates

- A support/control: **PASS**
- B primary effect/uncertainty: **FAIL**
- C year stability: **FAIL**
- D family robustness: **FAIL**

## Decision

`NO_GO_DEV_RANK2_NATIVE_REACTION`

Track A does NOT pass the preregistered DEV_RANK1 reaction gate; secondary slices are not allowed to rescue it.

The generic-control limitation remains unchanged: generic anchors are matched reference anchors, not proven treatment-free counterfactuals. Track A is conditional on exact J+1 contact and does not measure the unconditional value of all generated levels.
