# E display episode V1 — timing addendum

**Frozen:** 2026-08-29, before real outcome generation or reading.  
**Future-price outcomes used:** NONE.

This addendum closes one implementation detail of `XAUUSD_E_DISPLAY_EPISODE_PRE_OUTCOME_REPAIR_SPEC_v1_0_2026-08-29.md` before the canonical reaction labeler is implemented.

For a displayed snapshot with M1 open timestamp `t`:

- the snapshot is computed from the completed M1 bar and becomes available at `t + 1 minute`;
- its displayed geometry is valid from `t + 1 minute` inclusive until `t + 6 minutes` exclusive;
- if the same provenance-preserving display episode is present at the next C5 snapshot `t + 5 minutes`, the new geometry becomes available at `t + 6 minutes` and extends the episode without a gap;
- if the episode is absent at that next C5 evaluation, or the evaluation sequence is non-contiguous, the prior episode terminates at `t + 6 minutes`;
- no disappearance is backdated to `t + 1` or inferred from later reaction behavior.

An arming state is valid only while the display episode remains live under this rule. If the episode terminates before first contact, the arm state is discarded.

A contact bar with open timestamp exactly equal to a feature availability time uses that newly available snapshot. A bar with open timestamp exactly equal to the episode terminal time cannot use the expired episode unless a continuation snapshot is available at that same time.
