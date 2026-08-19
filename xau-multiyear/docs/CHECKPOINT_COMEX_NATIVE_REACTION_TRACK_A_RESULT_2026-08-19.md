# CHECKPOINT — COMEX native reaction Track A DEV_RANK1 result

Date: 2026-08-19  
Repository: `iagency971/twilio-voice-gateway`  
Branch: `agent/xau-comex-acquisition-plan`  
Status: **TRACK A OUTCOME EXECUTED / NO_GO DEV_RANK2**

## Authoritative result binding

Pre-outcome authority:

- artifact freeze commit: `93930f82c3168dfd02a05edc57b78811739db9eb`
- preoutcome freeze manifest SHA-256: `60713b922eefe24dd8fbc306c1f26cc2557c829ccd0080649afbc9071972ca47`

Track-A result publication:

- result publication commit: `710178def6c24d7d58f28beb17df0b4b27d123af`
- Track-A result manifest SHA-256: `26e0f08e103833ef78e911cb4f6c82bf5d59eadd90abc77bab9ed46d944cf8b5`
- protocol SHA-256 at execution: `ee77aaf57a0fdc72c8146c2e0938a22e0b8173b9b8d011216c639e18a1ebd97b`

The execution verified every frozen generated-artifact hash, regenerated the causal K=5 matcher and required exact identity with the frozen matched manifest before opening post-anchor prices.

## Primary result

Frozen confirmatory endpoint: pooled W15 `DELTA_NRB15`, equal-weighted by treated source/retest date.

- matched events: **227**
- matched treated dates: **81**
- `theta_NRB15`: **-0.01778503489907026**
- 95% percentile date-cluster bootstrap CI: **[-0.03899457780258087, 0.0012119706857348835]**
- date-weighted raw reaction-balance difference: **-3.6211934156379595 GC ticks**
- 50,000-draw two-sided sign-flip p: **0.08235835283294334**

Frozen primary Gate B required all of:

- `theta_NRB15 >= +0.02` — **FAIL**
- bootstrap 95% lower bound `> 0` — **FAIL**
- date-weighted raw reaction-balance difference `>= +2.0` ticks — **FAIL**

Gate B therefore fails unambiguously. The point estimate and raw-tick effect are on the opposite side of the preregistered positive-reaction target.

## Year stability Gate C

Only **2 of 8** yearly estimates are positive:

- 2011: +0.013248426891772897
- 2012: -0.0589533538633709
- 2013: +0.014069838274225232
- 2014: -0.01437039275911746
- 2015: -0.003165924157052619
- 2016: -0.02520164571064513
- 2017: -0.027962884246925616
- 2018: -0.03920498175242157

Every leave-one-year-out aggregate is negative. The maximum absolute yearly contribution share is 29.28%, so the concentration sub-gate passes, but the positivity/stability requirements fail.

Gate C: **FAIL**.

## Family robustness Gate D

W15 fixed family estimates:

- POC: +0.0017570465776252004
- VAH: -0.02664259494285095
- VAL: -0.029664924349387826
- VWAP: -0.01842353100285608

Only **1 of 4** families is positive, and POC is close to zero. Every leave-one-family-out aggregate is negative. The maximum absolute family contribution share is 45.81%, so the concentration sub-gate passes, but the family positivity/leave-one-out requirements fail.

Gate D: **FAIL**.

## Frozen secondary results

Family W15 Holm-adjusted tests:

- POC: theta +0.0017570, Holm p 0.9152
- VAH: theta -0.0266426, Holm p 0.3274
- VAL: theta -0.0296649, Holm p 0.4081
- VWAP: theta -0.0184235, Holm p 0.5379

None provides a Holm-significant positive W15 effect.

Aggregate secondary horizons:

- W5: theta -0.0148832, raw sign-flip p 0.01484, Holm p 0.04452
- W60: theta -0.0186977, Holm p 0.68319
- SC: theta +0.0751684, Holm p 0.68319

The W5 secondary is significantly negative after Holm, i.e. opposite the preregistered away/rejection direction. SC is positive but non-significant and is not allowed to rescue the failed primary W15 result.

## Decision

Gate A support/control: **PASS**  
Gate B primary effect/uncertainty: **FAIL**  
Gate C year stability: **FAIL**  
Gate D family robustness: **FAIL**

Frozen decision:

`NO_GO_DEV_RANK2_NATIVE_REACTION`

No best family, horizon, year, session, approach side or threshold may rescue this Track-A hypothesis post hoc.

## Interpretation boundary

This result rejects progression of the **specific preregistered Track-A hypothesis** that exact J+1 native COMEX POC/VAH/VAL/VWAP contacts exhibit a positive post-contact-minute away/rejection effect versus matched reference anchors.

It does not prove that every possible COMEX-derived trading strategy, later-lifetime Track B hypothesis, different independently preregistered market mechanism, or XAUUSD entry model is invalid. It does mean that this Track-A reaction hypothesis must not be advanced to DEV_RANK2 under the frozen rules.

The generic-control limitation remains: generic anchors are matched reference anchors, not proven treatment-free counterfactuals. That limitation cannot rescue a failed positive effect and is especially not a basis for post-hoc reinterpretation.

## Execution guard

- W15 opened: true
- reaction outcomes computed: true
- MFE/MAE: not computed
- order-dependent first-hit metrics: not computed
- XAUUSD economic mapping: not computed
- market-data API called: false
- market-data downloaded: false
- new market-data spend: 0
- DEV_RANK2 executed: false
- CONFIRM/RETRO_CONFIRM executed: false
- LOCKED_COMEX_TEST executed: false

## Bootstrap implementation note

The frozen matcher was regenerated once for all treated events and asserted exactly identical to the frozen manifest before outcomes. Because the frozen control universe and each event's causal matching covariates are fixed and matching is event-local, bootstrap resampling changes only treated-date cluster multiplicities. The execution therefore memoized the exact deterministic event-local rematch inside bootstrap draws rather than recomputing the identical lexicographic sort millions of times.

This implementation detail cannot change the NO_GO decision here: Gate B already fails on the preregistered point-estimate threshold and raw-tick threshold, and Gates C and D independently fail their fixed stability criteria.
