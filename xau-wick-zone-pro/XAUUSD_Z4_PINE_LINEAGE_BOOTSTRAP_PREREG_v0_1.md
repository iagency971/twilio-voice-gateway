# XAUUSD Z4 → Pine lineage bootstrap cap — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE CAP AUDIT METRICS  
**Scope:** engineering portability of the already validated M1 Z4 revisit model only.  
**Future outcomes permitted in this audit:** NONE.

## 1. Problem

The validated Z4 M0GL score uses causal lineage/stability state. A Pine implementation loaded on a chart cannot assume an infinite pre-existing lineage state; it needs a finite deterministic warm-up/bootstrap horizon.

Lineage matching itself in frozen Z4 is Markovian between consecutive eligible 15-minute landmarks. Older history affects only state variables carried by a matched lineage:

- age_active / age_civil;
- historical maximum prominence (`prom_vs_histmax`);
- consecutive prominence reinforcement streak;
- recent center/width histories (last 4 only).

The aim is to choose a finite bootstrap cap that reproduces the **frozen raw M0GL ranking** closely enough while minimizing Pine warm-up cost.

## 2. Data and reference

Use **DEV BID January–July 2024 only**, hash-locked to the already frozen DEV source manifest. Build the exact frozen Z4 dataset using engine blob:

`a8a147615c3fd366c49e93b340fd2018b5b66e9e`

Use frozen BID M0GL scaler/coefficients blob:

`c95fd545ec451968cb421f81ed6add0c508f387d`

No `revisited`, touch outcome, MFE/MAE, reclaim/retest, P&L or future price field may enter the audit.

## 3. Candidate caps frozen before results

Audit caps, in ascending order:

`C ∈ {96, 128, 160, 192}` eligible 15-minute lineage landmarks.

For each row, simulate a cold-start lineage state retaining at most the latest `C` consecutive appearances of that frozen lineage, including the current row:

- `age_lm_cap = min(age_lm_full, C)`;
- `age_active_min_cap = current_landmark_i - landmark_i_of_oldest_retained_lineage_row`;
- `age_civil_min_cap = current_time - time_of_oldest_retained_lineage_row`;
- `prom_vs_histmax_cap = current_prominence / max(prominence over retained lineage rows)`;
- `reinforce_streak_cap` = consecutive current backward chain of strictly increasing prominence, clipped by retained history;
- center shift, width/prominence/mass/strength one-step changes remain unchanged;
- center SD4 and width CV4 remain unchanged because they depend only on the latest four lineage rows and all candidate caps exceed four.

This is the exact state a cold-started Z4 lineage tracker would possess after the retained chain, because frozen lineage assignment depends only on the immediately preceding eligible landmark.

## 4. Outcome-blind metrics

For each cap compare capped frozen-M0GL raw output with the full-history frozen-M0GL raw output:

1. row-wise Pearson correlation;
2. row-wise Spearman correlation;
3. median / p90 / p95 / p99 absolute raw-score error;
4. proportion of rows with absolute raw-score error > 0.03 and > 0.05;
5. within-landmark Spearman (median and mean) when at least 3 zones exist;
6. top-1 zone agreement per eligible landmark;
7. top-3 set Jaccard per landmark where at least 3 zones exist;
8. share of rows whose full lineage age exceeds each cap;
9. full lineage-age max and selected quantiles.

## 5. PASS gate and deterministic cap selection

A candidate cap passes only if ALL hold:

- global raw-score Spearman ≥ **0.995**;
- global raw-score Pearson ≥ **0.995**;
- median absolute raw-score error ≤ **0.005**;
- p95 absolute raw-score error ≤ **0.030**;
- fraction with absolute error >0.05 ≤ **0.02**;
- median within-landmark Spearman ≥ **0.995**;
- top-1 zone agreement ≥ **0.95**;
- mean top-3 Jaccard ≥ **0.95**.

**Selection rule frozen now:** choose the *smallest* cap in `{96,128,160,192}` that passes every criterion. If none passes, finite-bootstrap port is NO-GO under this candidate set and a new outcome-blind architecture must be preregistered before further parity tests.

No threshold may be relaxed after seeing the audit.

## 6. Meaning of a PASS

A PASS authorizes using the selected cap to initialize lineage state in a Pine Z4 implementation. It does not validate trading reactions, profitability or higher timeframes, and it does not alter the already frozen scientific model.
