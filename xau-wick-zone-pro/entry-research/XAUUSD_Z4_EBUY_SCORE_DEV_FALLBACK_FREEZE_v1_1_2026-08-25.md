# XAUUSD Z4 — E_BUY_US DEV fallback freeze v1.1

**Frozen:** 2026-08-25 after E_BUY_US DEV v1.0, before any H2 reaction outcome is opened.  
**H2 status:** CLOSED.

## Reason for v1.1

The v1.0 preregistered model-selection rule selected `M2_HGB` by mean fold AP. M2 then failed exactly one final gate: E>=80 OOF count = 783 versus the preregistered minimum 800. No threshold is changed.

The already-evaluated fixed `M1_LOGISTIC` candidate from the same preregistration satisfied every original v1.0 gate without parameter change:
- pooled ROC AUC 0.7860742300635466;
- pooled AP 0.6060597424642136 versus baseline 0.2996897621509824;
- E>=80: N=837, positive rate 0.6762246117084827;
- E>=90: N=413, positive rate 0.738498789346247;
- E>=80 positive lift in all four temporal folds.

v1.1 is an explicit DEV fallback decision, not an independent validation and not a modification of the v1.0 thresholds.

## Frozen action

Freeze `M1_LOGISTIC` exactly as specified in v1.0:
- identical feature schema;
- identical train-only preprocessing definition;
- LogisticRegression L2, C=1.0, max_iter=2000, solver=lbfgs;
- fit once on all 7,110 resolved H1 BULL_REJECTION observations;
- save the exact fitted preprocessing/model object;
- save the sorted H1 fitted-score distribution as the empirical CDF used to map raw model scores to `E_BUY_US` percentile 0–100;
- record SHA-256 of model artifact, engine, v1.0 result and this freeze memo.

No new feature, parameter, label, threshold, family filter, time filter or H1 model comparison is authorized.

## Authorization

After the exact M1 artifact is frozen and hashed, create a new H2 validation preregistration before downloading or computing any H2 reaction outcome.

No production-score claim is made by this fallback freeze alone.
