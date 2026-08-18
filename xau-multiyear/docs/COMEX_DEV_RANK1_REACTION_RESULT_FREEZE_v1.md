# XAUUSD / COMEX — DEV_RANK1 reaction primary result freeze v1

Date: 2026-08-18
Status: DEV discovery result frozen before behavior/economic/native-zone interpretation.

## Scope

Target: existing preregistered `reaction_0_5sigma`.
Sample: 30,525 B2-causally-available events across 92 sessions, 2011–2018.
Validation: outer leave-one-year-out; ridge C selected by inner leave-one-year-out on remaining years. Same observations are used for B0/B1/B2.

Feature groups:
- B0 = XAU baseline;
- B1 = B0 + continuous GC M1 context;
- B2 = B1 + causal GC raw trades / auction features.

## Primary result

### B1 versus B0

- family-balanced event log-loss improvement: -0.0011996139721145993
- population event: -0.006861254991348487
- session-balanced: -0.006433051063948092
- positive outer years: 4/8
- session-cluster bootstrap 95% for family-balanced delta: [-0.01579820447093784, +0.014893085378449626]
- preregistered directional gate: FAIL

Interpretation: GC M1 context does not show robust incremental reaction predictiveness in this primary specification.

### B2 versus B1

- family-balanced event log-loss improvement: -0.011224265265382116
- population event: -0.02089932100325398
- session-balanced: -0.0199132020562941
- positive outer years: 2/8 (2017, 2018)
- session-cluster bootstrap 95%: [-0.020822901952018715, -0.0037311470784916856]
- preregistered directional gate: FAIL

Interpretation: the preregistered raw-trades/auction feature group materially worsens cross-fitted prediction of the binary reaction target relative to B1. This is not a reason to tune the feature group after seeing the outcome.

## Family diagnostics

B2 versus B1 is adverse under both population-event and session-balanced weighting for:
- CONFLUENCE;
- DOZ_ONLY;
- FVG_ONLY;
- OBJECTIVE_ONLY.

MEMORY_ONLY has only 118 events / 35 sessions. It shows a positive population-event delta but a negative session-balanced B2 delta. It is therefore INCONCLUSIVE and may not be promoted as a reaction-specific exception.

## Regularization audit

For every outer year and all B0/B1/B2 reaction fits, the inner LOYO selected C=0.01, the strongest regularization in the frozen grid. Thus the adverse B2 result is not rescued by the preregistered ridge penalty selection.

## Freeze decision

For target `reaction_0_5sigma` only:
- B1 is NOT eligible for DEV_RANK2 promotion on the current primary reaction model;
- B2 is NOT eligible for DEV_RANK2 promotion on the current primary reaction model;
- no post-hoc feature pruning, threshold search, family exception, or model-class change may convert this target into a primary pass.

This does NOT conclude that COMEX is globally useless. The preregistered behavior classification, entry eligibility/fill/net-R, and COMEX-native-zone studies remain distinct scientific questions and continue unchanged.
