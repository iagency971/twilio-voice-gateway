# XAUUSD Z4 → Pine grid-step compression — prereg v0.1

**Date:** 2026-08-23  
**Status:** FROZEN BEFORE GRID COMPRESSION METRICS  
**Scope:** engineering approximation of the already validated M1 Z4 revisit model.  
**Future outcomes used:** NONE.

## Motivation

The scientific Z4 engine uses a 0.01 USD price grid. That is practical in Python but expensive when reconstructing up to 96 historical 15-minute snapshots inside Pine. The already preregistered 3-box Gaussian approximation passed parity at 0.01. This gate asks whether a coarser, still absolutely aligned grid can reduce Pine cost without materially changing Z4 geometry or the frozen M0GL score ranking.

## Frozen reference

DEV BID January–July 2024, exact frozen Z4 at 0.01 USD with SciPy Gaussian.

Reference engine blob: `a8a147615c3fd366c49e93b340fd2018b5b66e9e`.

Frozen M0GL params blob: `c95fd545ec451968cb421f81ed6add0c508f387d`.

## Candidate Pine proxies

All proxies:
- retain the same 1,440 active-M1 memory;
- retain v60 and vseg definitions;
- retain 15-minute landmarks;
- retain Z4 family/peak/prominence/P50/feature/lineage logic;
- use the already parity-approved 3-box Gaussian approximation;
- use an absolute grid origin at 0.00 USD.

Only grid step changes.

Candidates: `0.02`, `0.05`, `0.10` USD.

The existing 0.01 3-box result is the fallback reference implementation if no coarser step passes.

## Matching and metrics

Use the same outcome-blind one-to-one geometry matching as the frozen 3-box parity audit. Compare each proxy with exact 0.01 Z4:

- exact-zone match rate;
- proxy-zone match rate;
- IoU distribution;
- center/boundary errors normalized by exact/proxy vseg;
- frozen M0GL raw-score Pearson/Spearman on matched zones;
- raw-score absolute error;
- within-landmark score rank correlation;
- matched top-1 zone agreement.

No future/contact/reaction/P&L field may be used.

## PASS gate frozen before results

A candidate passes only if ALL hold:

- exact-zone match rate ≥ **0.90**;
- proxy-zone match rate ≥ **0.90**;
- median IoU ≥ **0.80**;
- p10 IoU ≥ **0.55**;
- median center error ≤ **0.08 vseg**;
- p95 center error ≤ **0.25 vseg**;
- frozen raw-score Spearman ≥ **0.98**;
- frozen raw-score Pearson ≥ **0.98**;
- median absolute raw-score error ≤ **0.015**;
- p95 absolute raw-score error ≤ **0.060**;
- matched top-1 zone agreement ≥ **0.85**.

## Deterministic selection rule

Choose the **largest** grid step among `{0.02,0.05,0.10}` that passes every criterion, because runtime reduction is the sole engineering objective. If none passes, retain the previously passed 0.01 3-box implementation.

No threshold or candidate may be modified after viewing results.
