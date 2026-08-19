# XAU REJECTED STRATEGY HETEROGENEITY PROTOCOL v1

Date frozen: 2026-08-19
Status: `FROZEN_BEFORE_REJECTED_STRATEGY_SUBGROUP_OUTCOMES`
Parent evidence base: `XAU_CORE_EVIDENCE_AUDIT_V1`

## Purpose

Study whether Phase-C architectures that failed the original multiyear Vantage gate contain repeatable conditional structure by direction, session, zone age, timeframe/variant, or zone-session -> trade-session transition.

This is **hypothesis generation only**. No subgroup discovered here can rescue a rejected strategy, alter the validated core, become a production filter, authorize M5/COMEX, or justify a prop-firm challenge without a separately preregistered replication on independent data.

## Frozen historical universe

Use exactly the same Phase-C Vantage RAW research universe and execution definitions as `run_phase_c_vantage_raw.py`:

Samples:
- `DISPLACEMENT_ORIGIN_ONLY`
- `OBJECTIVE_LIQUIDITY_ONLY`
- `MEMORY_ONLY`
- `DOZ_OBJECTIVE_ONLY`

Structural entry models:
- `PASSIVE_TOUCH`
- `CLEAN_REJECTION`
- `FAILED_AUCTION`
- `ACCEPTANCE_RETEST`
- `RECLAIM_PULLBACK`

Touch model:
- `TOUCH_NEXT_OPEN` with frozen floors 0.25 / 0.50 / 0.75 / 1.00

RR surface:
- 0.5 / 1.0 / 1.5 / 2.0 / 2.5 / 3.0

Costs:
- `S10_C6`
- `S11_C6_PRIMARY`
- `S12_C6`
- `S18_C9_STRESS`

Years: 2011-2025.
Horizon: 120 minutes.

No strategy parameter may be changed.

## Integrity gate

Each annual reconstruction must reproduce the corresponding canonical `phase_c_vantage_raw_2011_2025/annual/<year>_summary.csv` for every Phase-C cell within floating-point tolerance before subgroup metrics are accepted.

Required parity metrics per cell:
- trades
- avg gross R
- avg net R
- PF net
- sum net R
- median risk price
- median entry delay

Failure is fail-closed for that year and for the aggregate analysis.

## Rejected architecture definitions

A **cell** is sample x entry model x risk rule x RR.

A **fully rejected architecture** is sample x entry model x risk rule for which none of the six RR cells has `survives_vantage_gate=True` in the canonical 2011-2025 multiyear summary.

A **partially surviving architecture** has at least one surviving RR and is reported separately, never mixed into the fully rejected set.

The already validated `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL` core is excluded from rejected-strategy candidate discovery and retained only as a reference benchmark.

## Frozen subgroup dimensions

For every architecture/cell, report:

1. direction: LONG / SHORT;
2. contact session;
3. entry session;
4. deterministic relevant-zone source timeframe;
5. deterministic relevant-zone variant;
6. relevant-zone tradable-age bucket;
7. origin session -> entry session;
8. activation/known session -> entry session.

Session buckets are the existing America/New_York buckets:
- ASIA_CME 18:00-02:59
- LONDON 03:00-07:59
- NY_AM 08:00-11:59
- NY_PM 12:00-15:59
- TRANSITION 16:00-17:59

Age buckets:
- <1h
- 1-4h
- 4-12h
- 12-24h
- 1-3d
- 3-7d
- 7-30d
- >=30d

Relevant deterministic anchor:
- pure DOZ: deterministic DOZ constituent;
- pure objective liquidity: deterministic objective-liquidity constituent;
- pure memory: deterministic memory constituent;
- DOZ+objective: report DOZ and objective anchors separately; the generic `relevant_zone` diagnostic uses the DOZ anchor for age/TF/variant and both family transitions are retained separately.

Anchor ordering is outcome-blind: smallest width, earliest known_time, earliest origin_time, lexical zone_id.

## Causal-clean diagnostic rule

Canonical Phase-C labels are reproduced first for parity. Subgroup discovery then uses a **causal-clean sensitivity**:

- a required constituent family must have at least one qualifying deterministic constituent with `known_time <= entry_time`;
- events that obtain a required sample family only through the +/-2 minute stack tolerance after the entry are excluded from causal-clean subgroup metrics;
- canonical and causal-clean counts are both reported.

This rule is fixed before subgroup outcomes and addresses the one-event causal defect discovered in the core audit.

## Candidate signal rules (descriptive, not validation)

A subgroup can be labelled `REPEATED_HYPOTHESIS_SIGNAL` only if all are true:

- belongs to a fully rejected architecture;
- at least 50 causal-clean trades at RR1.5 in the primary scenario;
- active in at least 10 of 15 years at RR1.5;
- mean net R > 0 in primary and stress at RR1.5;
- PF net > 1.10 in primary and >= 1.00 in stress at RR1.5;
- positive total net R in both primary and stress for at least 4 of the 6 RR values;
- subgroup outperforms its own architecture aggregate at the same RR in both primary and stress for at least 4 of 6 RR values.

A stronger label `ROBUST_HYPOTHESIS_SIGNAL` additionally requires:

- >= 100 causal-clean trades at RR1.5;
- >= 8 positive years at RR1.5 under primary costs;
- >= 7 positive years at RR1.5 under stress costs;
- positive primary and stress total R in at least 5 of 6 RR values.

These labels do not authorize trading or post-hoc strategy rescue.

## Cross-architecture recurrence

Also rank each subgroup feature (for example LONG, NY_AM, 1-3d) by how often it improves rejected architectures relative to their own aggregate. Cross-architecture recurrence is more informative than a single best cell.

## Outputs

Required:
- annual parity reports;
- architecture classification (fully rejected / partially surviving / validated reference);
- causal-invalid counts;
- subgroup metrics by dimension;
- session-transition metrics;
- RR-consistency metrics;
- cross-architecture recurrence table;
- candidate-signal table using the frozen rules above;
- a checkpoint explicitly separating `hypothesis generation` from `validated strategy`.

New paid market-data spend: 0.
