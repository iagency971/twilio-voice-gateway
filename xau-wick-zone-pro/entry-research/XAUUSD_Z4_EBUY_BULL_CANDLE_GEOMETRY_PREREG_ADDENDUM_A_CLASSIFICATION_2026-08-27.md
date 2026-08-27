# Addendum A — deterministic interpretation rules

**Frozen:** 2026-08-27 before the geometry runner is executed and before any new geometry outcome is inspected.

This addendum operationalizes the qualitative words `stable`, `broad` and `materially more reproducible` in the parent preregistration. It does not modify any candle feature, candidate definition, outcome, or sample.

## Session-bootstrap inference

Use whole-US-session bootstrap, seed `20260827`, 1000 draws. Report percentile 95% intervals.

## Continuous close-position signal

`close_pos` is considered reproducibly informative only if on H2 retrospective replication:
- session-bootstrap 95% CI for its raw-orientation AUC has lower bound > 0.50; and
- H1-defined top-quintile minus bottom-quintile TP1-rate difference has a 95% CI with lower bound > 0.

## Concentrated H1 change-point

The H1 close-position change-point bootstrap is called `CONCENTRATED` only if both:
- p90 - p10 <= 0.10 close-position units;
- p75 - p25 <= 0.05.

Otherwise it is `BROAD` and cannot support a hard-cutoff interpretation.

A concentrated H1 cutoff is called directionally replicated only if the exact H1 point estimate, without movement, produces on H2:
- positive rate above cutoff > positive rate below cutoff; and
- session-bootstrap 95% CI for the above-minus-below difference has lower bound > 0.

`STABLE_CLOSEPOS_CHANGEPOINT_CANDIDATE` additionally requires the H1 session-blocked cross-validated threshold-model mean log loss to be lower than the continuous-linear close_pos model mean log loss.

## Multivariate rejection geometry

The frozen 6-feature candle-only model supports `MULTIVARIATE_REJECTION_GEOMETRY` only if:
- H2 candle-model AUC has session-bootstrap 95% lower bound > 0.50; and
- H2 AUC(candle model) - AUC(close_pos-only frozen H1 logistic) has session-bootstrap 95% lower bound > 0.

No minimum AUC-delta magnitude is imposed beyond statistical directionality.

## Primary classification

Use priority:
1. `MULTIVARIATE_REJECTION_GEOMETRY` if its criteria pass;
2. else `STABLE_CLOSEPOS_CHANGEPOINT_CANDIDATE` if its criteria pass;
3. else `CONTINUOUS_GEOMETRY_SIGNAL` if continuous close-position criteria pass or another fixed geometry feature shows the same two-part reproducibility condition;
4. else `NO_GEOMETRY_SIGNAL`.

H2 remains retrospective replication, not pristine OOS. None of these classifications authorizes a Pine change without a fresh preregistered confirmation sample.