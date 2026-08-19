# CHECKPOINT — XAU core temporal stack integrity FAIL

Date: 2026-08-19  
Branch: `agent/xau-core-evidence-audit-v1`

## Terminal verdict

`TEMPORAL_STACK_INTEGRITY_FAIL_CORE_CLASSIFICATION_LOOKAHEAD`

The 15 annual audits from GitHub Actions run `32305748030` all completed successfully and each reproduced canonical stack semantics and the canonical historical core event set. The workflow aggregation job later failed only because pandas was absent from that aggregation environment; the authoritative totals below are a direct sum of the 15 already-successful annual artifacts.

## Exact 2011–2025 result

- canonical historical core events: **304 / 304**;
- core-classification temporal violations: **18**;
- violation rate: **5.9210526316%**;
- events missing a causal `DISPLACEMENT_ORIGIN` contact by CLEAN_REJECTION confirmation: **4**;
- events missing a causal `OBJECTIVE_LIQUIDITY` contact by confirmation: **14**;
- events containing at least one stack member that joined after confirmation: **21**;
- future member rows: **29**;
  - future DOZ members: **14**;
  - future objective members: **15**;
- temporal audit inspected/used P&L: **false**;
- new market-data spend: **0**.

## Annual violation counts

| Year | Core events | Violations | Missing DOZ | Missing objective |
|---:|---:|---:|---:|---:|
| 2011 | 16 | 1 | 0 | 1 |
| 2012 | 14 | 1 | 0 | 1 |
| 2013 | 17 | 3 | 0 | 3 |
| 2014 | 23 | 1 | 0 | 1 |
| 2015 | 27 | 2 | 1 | 1 |
| 2016 | 22 | 0 | 0 | 0 |
| 2017 | 27 | 2 | 0 | 2 |
| 2018 | 36 | 1 | 1 | 0 |
| 2019 | 21 | 0 | 0 | 0 |
| 2020 | 15 | 0 | 0 | 0 |
| 2021 | 18 | 5 | 0 | 5 |
| 2022 | 17 | 1 | 1 | 0 |
| 2023 | 17 | 0 | 0 | 0 |
| 2024 | 17 | 1 | 1 | 0 |
| 2025 | 17 | 0 | 0 | 0 |

Eleven of fifteen years contain at least one invalid historical classification. The defect is therefore not an isolated year or one anomalous trade.

## Root cause

`collapse_contact_events` allows geometrically overlapping first contacts occurring within a two-minute tolerance to join a common stack. The representative row carries one contact timestamp, while `constituent_families` can include a different-family contact whose own first contact occurs later. The historical `DOZ_OBJECTIVE_ONLY` sample used the merged family list without requiring both the DOZ and objective contacts to have occurred before the CLEAN_REJECTION confirmation / market-at-open entry.

Thus 18 historical trades were classified as DOZ+objective confluence using information that was not yet available at the decision boundary.

## Governance

The earlier statistical/portfolio result `CORE_INTERNAL_AUDIT_PASS_FOR_EXTERNAL_REPLICATION` remains an audit result for the original 304-event set but its authorization consequence is **suspended**.

Current status:

`CORE_EXTERNAL_REPLICATION_PASS_SUSPENDED_TEMPORAL_STACK_LOOKAHEAD`

Until Pro freezes a causal repair architecture:

- no external broker/feed replication;
- no live or prop-firm deployment;
- no M5 extension;
- no COMEX continuation experiment;
- no session/direction/age/A→B subgroup promotion;
- no rescue by deleting the 18 violating trades and re-quoting P&L.

The next step is a Pro architecture decision defining a fully causal confluence/stack representation before any repaired historical P&L is opened.

Machine-readable authority:

`xau-final-results/xau_core_temporal_stack_integrity_v1/temporal_stack_integrity_verdict.json`
