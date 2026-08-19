# XAU CORE TEMPORAL STACK INTEGRITY AUDIT v1

Date frozen: 2026-08-19  
Branch: `agent/xau-core-evidence-audit-v1`  
Status: `FROZEN_BEFORE_TEMPORAL_MEMBERSHIP_RESULTS`

## Purpose

A diagnostic from `XAU_CORE_EVIDENCE_AUDIT_V1` exposed one core event whose deterministic DOZ diagnostic anchor had `known_time` after the trade entry. This may be harmless anchor choice, or it may expose a causal defect in the 2-minute contact stacking: a representative contact can be joined by a different-family contact that occurs later, while the merged `constituent_families` label is then used to define `DOZ_OBJECTIVE_ONLY`.

This audit tests only temporal eligibility of stack constituents. It does not inspect or optimize P&L, sessions, direction, RR, stops, exits, or subgroups.

## Frozen population and engine

Reconstruct exactly the same 2011–2025 core population and canonical stack semantics used by the historical candidate and by `XAU_CORE_EVIDENCE_AUDIT_V1`:

- zone families and parameters unchanged;
- contact detection unchanged;
- canonical 2-minute `collapse_contact_events` unchanged;
- behavior and `CLEAN_REJECTION` entry unchanged;
- primary Vantage-like execution overlay used only to obtain the identical entry/confirmation indices;
- same public Dukascopy source and same annual warm-up/post-window rehydration;
- new market-data spend = 0.

## Membership reconstruction

The audit implementation must reproduce canonical stack representatives, geometry, constituent counts, families and variants exactly, while additionally retaining for each raw stack member:

- member zone ID;
- family and variant;
- zone origin time;
- zone known time;
- raw member contact index and contact timestamp.

Stack parity against canonical `collapse_contact_events` is mandatory.

## Frozen causal eligibility rule

For each executable historical `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION` core event:

1. compute the frozen confirmation index from the unchanged entry builder;
2. a stack member is `AVAILABLE_BY_CONFIRMATION` only if:
   - its zone `known_time` is no later than the end of the confirmation minute; and
   - its own raw contact index is `<= confirm_idx`;
3. the confluence classification is causally valid only if at least one `DISPLACEMENT_ORIGIN` member and at least one `OBJECTIVE_LIQUIDITY` member are `AVAILABLE_BY_CONFIRMATION`;
4. a member contacted on the entry minute is not allowed to establish confluence for a market-at-open entry because its intraminute contact is not known at the entry open.

The rule is outcome-independent and cannot improve any trade result.

## Required outputs

- one annual summary for each 2011–2025 year;
- one row for every violating core event;
- counts of future-joined members by family;
- count of events with missing causal DOZ by confirmation;
- count of events with missing causal objective level by confirmation;
- count of otherwise valid events containing additional future members;
- exact original core event count.

## Decision rule

- zero core-classification violations across all 304 events => `TEMPORAL_STACK_INTEGRITY_PASS`;
- one or more events lacking a causal DOZ or causal objective contact by confirmation => `TEMPORAL_STACK_INTEGRITY_FAIL_CORE_CLASSIFICATION_LOOKAHEAD`.

If FAIL, the prior `CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION` is suspended. No post-hoc removal of violating trades is permitted as a rescue. A causal stack/sample repair must be designed and the complete historical candidate must be rerun under that repaired definition before Pro can reconsider external replication.

## No-rescue / no-selection rule

This audit may not:

- remove violations and simply quote the remaining P&L;
- choose sessions, direction, age or subtype;
- change the two-minute tolerance after seeing violations;
- open M5 or COMEX continuation;
- authorize live or prop-firm trading.
