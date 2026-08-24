# XAUUSD Z4 → Pine lineage assignment simplification — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE ASSIGNMENT PARITY METRICS  
**Future outcomes used:** NONE.

## Purpose

Frozen Z4 uses Hungarian minimum-cost one-to-one matching between zones at consecutive eligible 15-minute snapshots. Pine does not provide a native Hungarian solver. Before implementing a custom solver, test a deterministic greedy minimum-cost matcher outcome-blind.

## Greedy candidate frozen now

At each eligible landmark:

1. create every valid previous/current pair using the exact Z4 validity rule;
2. compute the exact Z4 pair cost;
3. sort valid pairs ascending by `(cost, previous_row_index, current_row_index)`;
4. accept a pair iff neither row has already been assigned;
5. continue until all pairs exhausted;
6. unmatched current zones start new lineages;
7. a missing eligible snapshot terminates all previous lineages exactly as Z4.

All carried lineage-state formulas remain identical to Z4. Bootstrap is not truncated in this audit; this isolates assignment only.

## Data/reference

DEV BID January–July 2024, frozen exact Z4 zone geometry. Source and model hashes are already frozen. No future label may enter the comparator.

## Metrics

Compare greedy lineage state against frozen Hungarian lineage state on identical zone rows:

- previous-link agreement rate;
- lineage age exact agreement;
- absolute errors of age-active, age-civil, center-shift, changes, reinforce streak, center SD4, width CV4, prom-vs-histmax;
- frozen raw M0GL Pearson/Spearman;
- median/p95 raw-score absolute error;
- within-landmark Spearman;
- top-1 zone agreement;
- top-3 set Jaccard.

## PASS gate frozen before results

Greedy is authorized only if ALL hold:

- previous-link agreement ≥ **0.995**;
- raw-score Pearson ≥ **0.999**;
- raw-score Spearman ≥ **0.999**;
- median absolute raw-score error ≤ **0.002**;
- p95 absolute raw-score error ≤ **0.020**;
- median within-landmark Spearman ≥ **0.999**;
- top-1 agreement ≥ **0.995**;
- mean top-3 Jaccard ≥ **0.995**.

If any criterion fails, greedy is rejected and the Pine port must implement an exact/validated minimum-cost assignment method; thresholds will not be relaxed.
