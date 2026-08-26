# XAUUSD Z4 / E-BUY — Asia Core 21:00–03:00 NY reaction decision

**Date:** 2026-08-26  
**Session:** `21:00–03:00 America/New_York`  
**Cadence:** C5  
**Architecture:** `Z4 + ESM_BOTH_G120M + EPM_M1_R2_A8H + EWM_G60M + ES_M1_8H_R2_T0.50`  
**Final status:** `ASIA_CORE_ZONES_ONLY`

## Location authorization

The fresh August-2026 outcome-blind holdout passed all eight frozen localization/stability gates:
- coverage <=1v: 83.60%;
- <=1.5v: 93.46%;
- <=2v: 97.53%;
- nearest-zone p90: 1.168v;
- displayed-zone median: 2;
- displayed-zone p90: 3;
- survival-aware persistence: 97.81%;
- unexplained disappearance share: 2.19%.

Therefore Asia Core is authorized for **scientific E-BUY zone display**.

## Reaction preregistration

The reaction transfer floor was frozen before outcomes at:
- H1 TP1 resolved >=30%;
- H2 TP1 resolved >=30%;
- H1/H2 resolved share >=90%;
- duplicate contact guards;
- H2/H1 median target-distance and zone-width ratios inside [0.75, 1.25].

No `E_BUY_US` score was used.

## Historical reaction result

### H1 — 2024-08-01 to 2025-08-01
- contact episodes: 11,466;
- unique episode IDs: 11,465;
- Asia-Core sessions: 254;
- BULL_REJECTION fired: 4,822;
- TP1_FIRST: 1,319;
- INVALIDATION_FIRST: 3,220;
- NEITHER: 280;
- ambiguous: 3;
- resolved denominator: 4,819;
- **TP1 resolved rate: 27.3708% — FAIL vs 30%**;
- session bootstrap 95% interval approximately **25.19%–29.66%**;
- median fired TP distance: 5.2306v;
- median contacted-zone width: 0.25v.

### H2 — 2025-08-01 to 2026-08-01
- contact episodes: 12,386;
- unique episode IDs: 12,384;
- Asia-Core sessions: 256;
- BULL_REJECTION fired: 5,352;
- TP1_FIRST: 1,452;
- INVALIDATION_FIRST: 3,596;
- NEITHER: 301;
- ambiguous: 3;
- resolved denominator: 5,349;
- **TP1 resolved rate: 27.1453% — FAIL vs 30%**;
- session bootstrap 95% interval approximately **25.16%–29.13%**;
- median fired TP distance: 4.8136v;
- median contacted-zone width: 0.25v.

Geometry/duplicate guards passed:
- H2/H1 target-distance median ratio: ~0.9203;
- H2/H1 zone-width median ratio: ~1.00;
- no duplicate contact bookkeeping failure.

Thus the reaction failure is not explained by an obvious geometry or contact-duplication artifact.

## Fresh August-2026 reaction confirmation

On the same 14 complete frozen Asia-Core sessions from the fresh location holdout:
- contacts: 675;
- unique contact episodes: 675;
- BULL_REJECTION fired: 296;
- TP1_FIRST: 65;
- INVALIDATION_FIRST: 201;
- NEITHER: 30;
- **TP1 resolved rate: 21.9595%**;
- session bootstrap 95% interval approximately **14.57%–31.71%**;
- duplicate guard passed.

This fresh result does not rescue the failing H1/H2 reaction gate and is directionally weaker.

## Final authorization

Authorized in Asia Core 21:00–03:00:
- E-BUY zone computation/display only.

Not authorized in Asia Core:
- BULL_REJECTION scientific marker/alert;
- `E_BUY_US` rank;
- E>=80/E>=90 claim;
- BUY signal;
- BUY-zone memory;
- BUY alert.

US 08:00–17:00 scientific behavior remains unchanged.

The Pine v2.4.6 patch must encode this separation explicitly.