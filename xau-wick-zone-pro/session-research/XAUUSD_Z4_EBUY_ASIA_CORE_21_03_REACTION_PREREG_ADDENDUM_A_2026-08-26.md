# Asia Core 21:00–03:00 reaction prereg — Addendum A

**Frozen before reaction outcomes are generated or inspected.**

This addendum makes the anti-artifact diagnostics quantitative.

## Geometry guard

For H1 vs H2 retrospective windows:

- median fired TP distance in v ratio `H2/H1` must be within `[0.75, 1.25]`;
- median contacted-zone width in v ratio `H2/H1` must be within `[0.75, 1.25]`.

If a denominator is zero/non-finite, the reaction transfer gate fails.

These are not optimization targets; they only prevent crediting a result that depends on materially easier target or invalidation geometry in one window.

## Bootstrap

Use 10,000 fixed-seed (`20260826`) resamples of **Asia-Core session IDs with replacement** within H1 and H2 separately. Each sampled session contributes its complete BULL_REJECTION fired outcome counts. Report percentile 2.5% / 97.5% intervals for TP1 resolved rate. Bootstrap intervals are diagnostic and do not replace the preregistered 30% point-estimate gate.

## Fresh August 2026

The fresh August reaction sample is reported on exactly the complete session IDs frozen by the location holdout. No minimum count or success threshold is introduced after the fact. It is a directional confirmation / contradiction diagnostic only and cannot rescue a failing H1 or H2 gate.

## Decision

`ASIA_CORE_BR_REACTION_PASS` requires the seven parent-prereg conditions plus both geometry-ratio guards above.