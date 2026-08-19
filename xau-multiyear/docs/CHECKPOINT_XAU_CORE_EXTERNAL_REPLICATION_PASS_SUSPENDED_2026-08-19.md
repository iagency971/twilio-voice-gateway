# CHECKPOINT — XAU core external-replication PASS suspended

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-core-evidence-audit-v1`

## Status

`CORE_EXTERNAL_REPLICATION_PASS_SUSPENDED_TEMPORAL_STACK_LOOKAHEAD`

The statistical/portfolio audit in `xau-final-results/xau_core_evidence_audit_v1/` correctly reproduced the historical 304-event candidate and passed its frozen integrity, bootstrap, temporal, concentration and one-position portfolio gates **for that historical event set**.

However, a later outcome-independent temporal-membership audit discovered that the historical event-set construction itself is not fully causal.

## Root cause

Canonical `collapse_contact_events` allows geometrically overlapping first contacts occurring within a two-minute tolerance to join one stack. The representative row retains one contact timestamp, while `constituent_families` can include a member whose own first contact occurs later.

The historical `DOZ_OBJECTIVE_ONLY` sample was then defined from merged `constituent_families` without requiring at least one `DISPLACEMENT_ORIGIN` contact and at least one `OBJECTIVE_LIQUIDITY` contact to have occurred before the CLEAN_REJECTION confirmation / market-at-open entry.

Therefore a historical trade can be labeled as DOZ+objective confluence using a family contact that was not yet observable at the decision time.

## Frozen causal audit

Authority:

`xau-multiyear/docs/XAU_CORE_TEMPORAL_STACK_INTEGRITY_PROTOCOL_v1.md`

The audit does not use P&L. It verifies exact canonical stack parity and exact historical core event-set identity, then asks whether both required family contacts were causally available by the frozen CLEAN_REJECTION confirmation index.

## Confirmed evidence already sufficient to suspend the PASS

Completed annual results include:

- 2011: 16 core events, 1 core-classification violation;
- 2012: 14 core events, 1 violation;
- 2013: 17 core events, 3 violations;
- 2014: 23 core events, 1 violation;
- 2015: 27 core events, 2 violations.

Thus the first five completed years contain 97 historical core trades and 8 causal-classification violations.

Most early violations are caused by an `OBJECTIVE_LIQUIDITY` member joining after confirmation. At least one completed year (2015) also contains a missing causal DOZ case, showing that the issue is in temporal stack-family classification generally rather than one objective subtype.

The 2013 audit is especially explicit:

- stack parity: PASS;
- canonical core event set: PASS;
- 17 core events;
- 3 violations;
- all 3 lacked a causally contacted objective member by confirmation;
- P&L inspected/used by temporal audit: false.

Examples include historical entries occurring before the objective-level first contact that later joined the two-minute stack.

## Governance consequence

The previous terminal label:

`CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION`

is **not deleted** because it remains the correct result of the frozen statistical audit applied to the original historical event set. But its authorization consequence is suspended because the event-set definition has now failed a stricter causal-integrity check.

Until a Pro review decides and freezes a causal repair:

- external feed/broker replication is NOT authorized;
- live/prop-firm use is NOT authorized;
- M5 is NOT authorized;
- COMEX continuation is NOT authorized;
- session/direction/age/A→B diagnostic subgroups from the 304-event sample are hypothesis-generation only;
- no subgroup may be promoted as a trading filter;
- violating trades may NOT simply be removed and the remaining P&L quoted as a rescue.

## Required next scientific step

Finish the already-running 2011–2025 temporal-stack audit only to quantify the full defect.

Then return to **Pro** for a repair-architecture decision before changing stack semantics or rerunning strategy P&L.

Any repaired candidate must be rebuilt from a fully causal confluence definition and rerun across the complete historical development panel under a newly frozen protocol. The old 304-event profitability statistics cannot be carried forward as validation of the repaired event set.

New market-data spend during this defect audit: 0.
