# Addendum A — C1/C5 causal active-interval convention

**Frozen:** 2026-08-26, after code inspection and before generating or inspecting any new C1 H1/H2 reaction outcome.  
**Parent preregistration:** `XAUUSD_Z4_C1_REFRESH_EBUY_PREREG_v1_0_2026-08-26.md`  
**Outcome status at freeze:** no new C1 H1/H2 reaction result has been generated or inspected.

## 1. Outcome-blind implementation issue discovered before the run

The currently frozen C5 reaction implementation evaluates price rows strictly after a C5 state timestamp and strictly before the next C5 state boundary. Therefore a C5 state at `t` with the next state at `t+5m` observes the four intermediate M1 rows and excludes the row stamped at the next state boundary.

Applying that exact boundary-exclusion mechanically to C1 would create a degenerate reaction window: consecutive C1 states are one minute apart, leaving no complete M1 row strictly between them. C1 would therefore have zero opportunity to register a fresh M1 contact. That would not test the research question.

This is a timing-definition issue, not an outcome result. It was identified by source inspection before any new C1 H1/H2 reaction output.

## 2. Symmetric causal active-interval control

The cadence comparison will therefore report a separate, symmetric control named `CAUSAL_ACTIVE_INTERVAL_V1`.

A state whose geometry is confirmed using the completed M1 observation stamped `t`:

- cannot act on that same M1 observation;
- becomes usable immediately after `t`;
- governs subsequent M1 price observations until the next cadence state becomes confirmed;
- the M1 observation stamped at the next cadence boundary belongs to the *prior* state for intrabar/contact purposes, because the new state is only known after that M1 observation is complete;
- the new state begins governing only after its own boundary observation completes.

Operationally, for contiguous data:

- C1 state at `t` governs exactly the next M1 observation `t+1m`;
- C5 state at `t` governs `t+1m ... t+5m` inclusive;
- there is no same-bar lookahead for either cadence.

If a required next raw M1 observation is missing, no synthetic observation is created. C1 display lineage still follows the parent preregistration: non-contiguous C1 scientific states do not receive one-step continuity credit.

## 3. Relationship to the existing frozen C5 baseline

The existing source-faithful C5 baseline remains mandatory as a provenance anchor:

- H1: 19,878 eligible snapshots / 16,895 contacts / 7,127 BR / TP1 resolved 31.4390209593%;
- H2: 20,382 eligible snapshots / 17,578 contacts / 7,643 BR / TP1 resolved 30.1296320545%.

Those reaction counts use the already-frozen boundary-exclusion implementation and must not be silently rewritten.

Therefore the study will distinguish:

1. `FROZEN_C5_BASELINE` — immutable provenance/reference evidence;
2. `CAUSAL_ACTIVE_INTERVAL_V1_C5` — C5 re-evaluation under the symmetric causal timing convention;
3. `CAUSAL_ACTIVE_INTERVAL_V1_C1` — C1 under the identical causal timing convention.

The causal C1-vs-C5 comparison is the valid cadence-effect comparison. Differences between frozen C5 and causal-control C5 quantify the timing-convention effect and are not attributed to cadence.

## 4. Reaction geometry remains frozen at contact

All other parent-preregistered rules remain unchanged:

- BULL_REJECTION is the primary trigger;
- top-3 scientific E zones remain separate;
- a zone must be armed causally before contact;
- contact-state `center/zlo/zhi`, `v_contact`, and upper-Z4 target are frozen once contact occurs;
- later cadence refreshes cannot move the invalidation or target of an already-contacted episode;
- invalidation remains the first confirmed M1 close strictly below frozen `zlo`;
- evaluation ends at 17:00 New York same session;
- no E-score refit/recalibration is permitted.

## 5. Decision impact

No C1 result may be promoted from the immutable frozen-C5 baseline alone. The cadence decision must use the symmetric `CAUSAL_ACTIVE_INTERVAL_V1` comparison plus the preregistered stability/churn diagnostics.

This addendum does not authorize any Pine change or any production replacement of C5.