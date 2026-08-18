# XAUUSD / COMEX — DEV_RANK1 multiclass behavior primary result freeze v1

Date: 2026-08-18
Status: full primary behavior result frozen before binary diagnostic / entry-economic interpretation.

## Scope

Target: preregistered multiclass `behavior_v2`:
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTED_BREAK
- UNRESOLVED

Sample: 30,525 B2-causally-available events / 92 sessions / 2011–2018.
Validation: exact nested leave-one-year-out. The monolithic job hit a GitHub runtime limit; the scientific computation was recovered as 24 independent outer folds (8 years × B0/B1/B2), importing the exact original modeling functions, same solver (`lbfgs`), same `max_iter=500`, same C grid, same features and same observations. All 24 folds completed successfully before aggregation.

## B1 versus B0 — already frozen independently

- family-balanced event log-loss improvement: -0.08895647681196683
- population-event: -0.016060680627900115
- session-balanced: -0.015393042682600222
- positive years: 1/8
- session-cluster bootstrap 95%: [-0.18509828602253298, -0.014713994851130466]
- directional gate: FAIL

Conclusion: continuous GC M1 context does not improve the primary multiclass behavior target.

## B2 versus B1 — final primary result

- family-balanced event log-loss improvement: **-0.041492783889132356**
- population-event: **-0.03876402245365618**
- session-balanced: **-0.037418486640243165**
- positive outer years: **2/8**
- year deltas:
  - 2011: -0.05759945016303014
  - 2012: -0.03332103523464658
  - 2013: -0.0647978988732012
  - 2014: -0.21567257747578727
  - 2015: +0.013849546466969453
  - 2016: -0.00714488366726207
  - 2017: +0.007435834022183951
  - 2018: -0.01543775509014178
- trading-date cluster bootstrap 95%:
  - lo: **-0.0702123867460549**
  - median: -0.04140937002684175
  - hi: **-0.011280598334848674**
- directional gate: **FAIL**

## Pooled metrics

Family-balanced:
- B0 log-loss 0.7770071722990284 / macro-Brier 0.10511954896900468 / accuracy 0.6979727696860055
- B1 0.8659636491109952 / 0.10894909885315558 / 0.6830879689179394
- B2 0.9074564330001276 / 0.11435868566932214 / 0.6669981644298111

Population-event:
- B0 0.7194975759902124
- B1 0.7355582566181125
- B2 0.7743222790717686

Session-balanced:
- B0 0.7190385432397328
- B1 0.734431585922333
- B2 0.7718500725625762

Thus the degradation is not an artifact of one weighting convention.

## Family diagnostics for B2 versus B1

Both population-event and session-balanced log-loss deltas are adverse for:
- CONFLUENCE: -0.033883 / -0.065085
- DOZ_ONLY: -0.054586 / -0.040787
- FVG_ONLY: -0.038719 / -0.037557
- MEMORY_ONLY: -0.047456 / -0.081097 (small: 118 events / 35 sessions)
- OBJECTIVE_ONLY: -0.032819 / -0.036847

No broad family qualifies as a primary behavior exception.

## Freeze decision

For the preregistered multiclass behavior target:
- B1 is NOT eligible for DEV_RANK2 promotion;
- B2 is NOT eligible for DEV_RANK2 promotion;
- no post-hoc pruning, threshold search, family exception, behavior remapping, solver change or model-class change may convert this primary target into a pass.

This result does NOT establish that COMEX is globally useless. The already-preregistered distinct questions remain open:
1. entry eligibility/fill at model-specific causal decision times;
2. net-R conditional on fill under frozen execution/cost rules;
3. COMEX-native source zones and future exact-tape retests.

The secondary binary REJECT-vs-ACCEPT diagnostic may aid interpretation but cannot override this multiclass primary failure.
