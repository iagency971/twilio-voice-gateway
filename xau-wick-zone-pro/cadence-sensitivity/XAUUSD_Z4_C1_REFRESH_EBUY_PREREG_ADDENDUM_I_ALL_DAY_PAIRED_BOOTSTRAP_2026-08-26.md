# XAUUSD Z4 / E-BUY — C1 refresh preregistration Addendum I: all-common-day paired bootstrap

**Frozen:** 2026-08-26, before any valid H1/H2 C1 reaction outcome is opened or interpreted.  
**Scope:** paired uncertainty implementation correction only; point estimates and reaction rules unchanged.

## Pre-existing frozen rule

The parent preregistration requires paired trading-day or week blocks and 10,000 bootstrap replications with fixed seed `20260826` where matching is feasible.

## QA finding

The provisional helper formed the bootstrap day set as the union of days appearing in fired-trade records. Days on the common trading support with zero fired trades in both variants were therefore absent. Those zero/zero days do not change the pooled point estimate, but omitting them can understate day-level sampling variability.

## Required correction

The authoritative paired-day bootstrap for the final C1 cadence decision must:

- use the exact `common_raw_trading_days` from the pre-frozen common-session support rule;
- include every common NY trading day, including zero/zero days;
- for each day, aggregate TP1_FIRST numerator and non-ambiguous resolved denominator separately for C1 and its C5 comparator;
- sample the full day vector with replacement, preserving paired C1/C5 day blocks;
- use 10,000 replications and seed `20260826`;
- report the pooled C1-minus-C5 TP1 resolved-rate point difference and percentile 95% interval;
- apply identically to the primary C1-vs-mechanical-C5 comparison and the source-faithful C5 bridge comparison.

Any earlier fired-day-only bootstrap is diagnostic only and must not be used for the final promotion/retention verdict.

**Authorization:** uncertainty-estimation repair only. No outcome, trigger, geometry, contact, target, invalidation, Pine, or production rule changes.