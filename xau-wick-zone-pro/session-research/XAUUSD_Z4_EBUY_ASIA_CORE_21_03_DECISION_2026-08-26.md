# XAUUSD Z4 / E-BUY — Asia Core 21:00–03:00 decision

**Date:** 2026-08-26  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Session:** `21:00–03:00 America/New_York`  
**Cadence:** C5  
**Scientific scope authorized:** E-BUY zone-location display only  
**E_BUY_US / BULL_REJECTION / BUY authorization for Asia:** NONE

## Evidence basis

The full Asia transfer window `18:00–03:00 NY` failed the preregistered H1 location gate. A fixed outcome-blind diagnostic showed that the deficit was concentrated in `18:00–21:00`, while the later Asia window was materially stronger. The resulting `21:00–03:00` hypothesis was therefore treated as post-diagnostic and was not declared validated from H1/H2.

A fresh outcome-blind holdout was preregistered on Dukascopy BID August 2026, not used in the prior H1/H2 Asia studies. Source was frozen before metrics:

- file: `xauusd_bid_m1_2026_08.csv`;
- SHA-256: `4f61d531018a8e8c37b1f410945e1d23d59fee96cde13bef223dcc9e63d0f852`;
- rows: `24,115`;
- observed source span: `2026-08-02T00:00:00Z` → `2026-08-20T23:58:00Z`.

Holdout workflow: `33020549015` (`XAU Z4 E-BUY Asia Core Aug2026 Location v1`).

## Fresh holdout result

Status: `ASIA_CORE_FRESH_AUG2026_LOCATION_PASS`.

- complete source session IDs: 19;
- eligible Asia-Core sessions: 14;
- eligible snapshots: 811;
- zero-display share: 2.4661%;
- mean displayed zone count: 2.1973;
- median displayed zone count: 2;
- p90 displayed zone count: 3;
- coverage <=0.5v: 58.9396%;
- coverage <=1.0v: **83.6005%** (PASS >=80%);
- coverage <=1.5v: **93.4649%** (PASS >=90%);
- coverage <=2.0v: **97.5339%** (PASS >=95%);
- nearest-zone median: 0.3871v;
- nearest-zone p90: **1.1677v** (PASS <=1.5v);
- survival-aware persistence: **97.8060%** (PASS >=70%);
- unexplained survival-eligible disappearance: **2.1940%** (PASS <=5%).

All eight preregistered location/stability checks pass.

## Pine implementation authorization

This evidence authorizes a Pine QA candidate in which the existing frozen C5 E-BUY **zone-location architecture** is displayed during `21:00–03:00 NY` in addition to the existing US context.

The Pine candidate MUST keep Asia Core zones scientifically separated from the US reaction/score layer:

- no `E_BUY_US` score is computed or interpreted for Asia Core;
- no Asia BULL_REJECTION trigger is promoted to a validated BUY;
- no Asia BUY alert is generated;
- the existing US 08:00–17:00 behavior, score, trigger, next-open execution and alerts remain unchanged;
- Asia labels must not imply a calibrated E score; they should identify the E1/E2/E3 zone slot and indicate Asia / zones-only state;
- outside US and Asia Core, E-BUY display remains inactive;
- no change to Z4 geometry, ESM/EPM/EWM/ESwing parameters, local band, dedup, sticky carry, C5 cadence or warm-up.

## Nonclaims

The August 2026 holdout is partial-month and validates only location/stability for this new session window. It does not validate:

- Asia BULL_REJECTION reaction quality;
- Asia TP1/invalidation rates;
- the frozen US E score in Asia;
- profitability, spread/slippage robustness or production BUY signals in Asia.

A separate preregistered reaction study is required before enabling Asia BR/E-score/BUY logic.