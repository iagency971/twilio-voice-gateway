# XAUUSD Z4 / E-BUY — Asia session study preregistration v1.0

**Frozen:** 2026-08-26, before any new Asia-session reaction result is generated or inspected.  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** BUY-only, C5 cadence, retrospective session-transfer sensitivity.  
**Production authorization:** NONE.

## 1. Research question

Test whether the existing scientific E-BUY zone architecture can operate during the Asia/overnight session with acceptable location coverage and stability, and, only if that outcome-blind gate passes, whether the same frozen zone/contact semantics produce coherent BULL_REJECTION reactions in H1 and H2.

This is a session-transfer study. It does not refit or reuse the frozen US E score as if it were calibrated for Asia.

## 2. Frozen Asia session

Use the session partition already present in the Z4 detector:

- **ASIA / OVERNIGHT:** New York local time `18:00 <= time < 24:00` OR `00:00 <= time < 03:00`;
- London/Europe remains `03:00–08:00 NY` and is outside this study;
- US remains `08:00–17:00 NY` and is the existing validated context;
- rollover `17:00–18:00 NY` remains excluded.

No Asia window may be adjusted after results are viewed.

## 3. Frozen scientific state

Keep unchanged:

- cadence: **C5**;
- Z4 detector geometry and lookback: unchanged;
- E-BUY architecture: `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`;
- top-3 displayed BUY zones;
- local band `0 < distance <= 2.0v`;
- sticky carry/matching rules;
- `0.20v` internal de-duplication tolerance;
- no scientific fusion of E1/E2/E3;
- warm-up: 96 C5 landmarks (~480 minutes), unchanged.

Only the eligible session filter changes from US to ASIA/OVERNIGHT.

## 4. Data and windows

Use the same frozen Dukascopy BID M1 source manifest/hashes already used by the current E-BUY evidence.

- H1: `2024-08-01T00:00:00Z <= t < 2025-08-01T00:00:00Z`;
- H2: `2025-08-01T00:00:00Z <= t < 2026-08-01T00:00:00Z`.

The study is retrospective session-transfer sensitivity, not pristine OOS validation.

## 5. Outcome-blind location/stability gate

H1 and H2 must be reported separately. For each window report:

- eligible snapshot count;
- displayed-zone count mean/median/p90;
- coverage within 1.0v / 1.5v / 2.0v;
- nearest-zone distance median/p90;
- raw display persistence;
- survival-aware display persistence;
- unexplained disappearance share;
- crossed-below / no-longer-local / hidden-underlying shares;
- candidate-family mix;
- session-state runtime.

Reuse the pre-existing operational E-BUY thresholds rather than inventing Asia-specific thresholds after results:

1. coverage <=1.0v >= 0.80;
2. coverage <=1.5v >= 0.90;
3. coverage <=2.0v >= 0.95;
4. displayed-zone count median between 1 and 3;
5. displayed-zone count p90 <= 3;
6. nearest distance p90 <= 1.5v;
7. survival-aware display persistence >= 0.70;
8. unexplained share of survival-eligible transitions <= 0.05.

**Reaction study authorization requires all eight checks to pass in both H1 and H2.** If either window fails, stop and retain US-only scientific authorization for the current E-BUY engine.

## 6. Reaction semantics if location gate passes

Use BULL_REJECTION only. Keep the same causal contact rules, adapted to the Asia session boundary:

- displayed BUY zone must be below price and local;
- at least one causal upper Z4 target must exist;
- zone must be armed by a confirmed close above current `zhi`;
- fresh contact = first later M1 range overlap after arming;
- max one fresh contact per display episode per Asia session;
- freeze contact-state `center/zlo/zhi`, `v_contact`, and nearest causal upper-Z4 TP1 at contact;
- invalidation = first confirmed M1 close strictly below frozen contact `zlo`;
- evaluation ends at **03:00 NY** for that Asia session;
- no target or invalidation may move after contact.

Because the Asia session crosses midnight, session identity is anchored to the New York calendar date on which the session starts at 18:00. Bars from 00:00–02:59 belong to the prior session-start date.

## 7. Mandatory reaction diagnostics

For H1 and H2 separately report:

- fresh contact episodes;
- BULL_REJECTION fired count/share;
- TP1_FIRST / INVALIDATION_FIRST / NEITHER / AMBIGUOUS;
- resolved denominator;
- TP1 resolved rate;
- invalidation resolved rate;
- contacts and fired events per Asia session;
- zone width in v;
- target distance in v;
- time to TP/invalidation;
- origin-family mix;
- early-evening vs post-midnight subperiod diagnostics when denominator is adequate.

No gain may be attributed to Asia if it is explained mainly by altered invalidation geometry, target distance, duplicate contacts, or session-boundary bookkeeping.

## 8. E score exclusion

The existing frozen E score is US-context and contains cadence/session-specific learned relationships. It is **not** a calibrated Asia probability.

Therefore:

- no E>=80/E>=90 Asia claim;
- no model refit;
- no recalibration;
- no production score transfer.

If Asia zones/reactions prove promising, an Asia-specific E-score study must be preregistered separately.

## 9. Decision rule

Asia may be labelled `PROMISING_RETROSPECTIVE_ASIA_SESSION` only if:

1. all eight outcome-blind location/stability checks pass in H1 and H2;
2. reaction direction is coherent in H1 and H2;
3. the apparent reaction quality is not primarily a mechanical artifact of invalidation/target distance/contact duplication;
4. runtime remains operationally feasible;
5. no US-model score is used to manufacture the result.

Otherwise retain the current scientific authorization as US-only and do not enable scientific Asia signals in Pine.

Even a favorable result remains retrospective and does not itself authorize production.
