# XAUUSD Z4 — FOREXCOM transfer pilot preregistration v0.1

**Frozen:** 2026-08-25  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Purpose:** outcome-blind feed-transfer viability test only. No revisit/reaction/P&L outcome may enter any metric or selection.

> **Technical verification note (2026-08-25):** the first workflow attempt stopped in the prereg text-verification step, before any Dukascopy acquisition or feed metric was executed. The workflow sentinel used the wording `target timestamp coverage of FOREXCOM active M1 >= **97%**` while the frozen rule below says `common timestamp coverage ... >= **97%**`. These phrases denote the same denominator defined by the gate. This note adds the exact sentinel alias only; no threshold, dataset, model, metric, matching rule or verdict rule is changed.

## Scientific state entering this test

- Z4 scientific reference feed: Dukascopy XAUUSD BID.
- Selected cadence: C5 (5-minute snapshots).
- LOOKBACK: 1440 active M1.
- Frozen C5 BID M0GL model and C5 DEV-only R map remain unchanged.
- TradingView `FOREXCOM:XAUUSD` metadata reports `bar_source = mid`; therefore the **primary transfer pair is Dukascopy synthetic MID vs FOREXCOM MID**.
- Dukascopy BID vs FOREXCOM MID is a support/control pair and does not override the primary pair.
- This pilot uses the exact FOREXCOM history obtainable without an authenticated TradingView session. A pilot PASS does **not** by itself validate multi-month feed transfer.

## Data window

Use the exact timestamp intersection of:

1. the published `FOREXCOM:XAUUSD` M1 depth-test data; and
2. Dukascopy BID+ASK M1 for the same calendar period.

Each feed is processed natively (its own active M1 sequence). Comparison is by common UTC timestamp, not by native active-row index.

The first 1440 active M1 are detector lookback only. Additionally, the first 96 C5 landmarks after detector eligibility are excluded from score/R gate metrics to avoid interpreting cold-start lineage as mature transfer evidence.

## No-future-outcome engine rule

The C5 feed-parity engine must be a mechanical geometry/lineage-only derivative of canonical Z4:

- cadence only: 15 min -> 5 min;
- no call to `outcome_zone`;
- no `revisited`, MFE/MAE, sweep/reclaim, reaction, RR, P&L or future label may be computed or used;
- end-of-sample geometry must not require a future horizon.

## Raw-feed diagnostics

Primary: Dukascopy synthetic MID vs FOREXCOM MID.

Gate:

- common timestamp coverage of FOREXCOM active M1 >= **97%**;
- Pearson correlation of common 1-minute close-to-close returns >= **0.95**;
- Spearman correlation of common 1-minute close-to-close returns >= **0.95**.

Unadjusted OHLC/close price gaps are reported but are diagnostics, not promotion gates, because a persistent provider level offset is compatible with a native-feed overlay. The zone gate below therefore compares both absolute coordinates and **close-aligned structural coordinates**.

## Zone matching

At each common mature C5 timestamp and side, match zones one-to-one with Hungarian assignment.

Primary structural coordinates are local-to-feed price coordinates:

- `center_rel = center - close(feed, landmark)`;
- `zlo_rel = zlo - close(feed, landmark)`;
- `zhi_rel = zhi - close(feed, landmark)`.

A candidate pair is matchable when relative-center distance <= max(vseg_ref, vseg_target) or relative zones overlap. Matching cost remains center-distance/vseg + 0.5*(1-IoU) + 0.1*|log(width_target/width_ref)|.

Primary MID->FOREXCOM viability thresholds:

- Dukascopy zone match rate >= **0.80**;
- FOREXCOM zone match rate >= **0.80**;
- median close-aligned IoU >= **0.70**;
- p10 close-aligned IoU >= **0.30**;
- median close-aligned center error <= **0.25 vseg**;
- p95 close-aligned center error <= **0.75 vseg**.

Absolute-coordinate IoU and center error are reported separately but do not override the structural primary gate.

## Frozen M0GL score transfer

Apply the **same frozen Dukascopy BID C5 M0GL model** to both native feed feature tables. No refit, recalibration, coefficient change or feed-specific normalization is allowed.

On matched mature zones:

- raw-score Spearman >= **0.90**;
- median absolute raw-score difference <= **0.07**;
- p95 absolute raw-score difference <= **0.20**;
- matched top-1 zone agreement per common landmark >= **0.70**.

## Frozen R-map transfer

Apply the existing C5 Dukascopy DEV percentile map to both raw scores. No FOREXCOM-specific R remapping is allowed in this pilot.

Gate:

- R Spearman >= **0.90**;
- at least **80%** of matched displayed integer R values within +/-10 points;
- at least **95%** within +/-20 points.

`R` remains a rank of frozen revisit-likelihood score, not a probability and not reaction strength.

## Verdict taxonomy

- `PILOT_PASS_TRANSFER_VIABLE`: all primary MID->FOREXCOM thresholds pass. This authorizes seeking deeper/history-authenticated transfer evidence; it does **not** promote FOREXCOM to validated scientific feed.
- `PILOT_FAIL_TRANSFER_NOT_SUPPORTED`: one or more primary thresholds fail. Do not promote FOREXCOM; diagnose before any model/feed adaptation.
- `PILOT_INSUFFICIENT_DATA`: data identity/coverage or mature common landmarks are insufficient to run the frozen gate.

The Dukascopy BID->FOREXCOM control is reported independently and cannot rescue a primary MID failure.
