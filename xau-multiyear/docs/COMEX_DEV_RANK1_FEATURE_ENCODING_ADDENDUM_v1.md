# COMEX DEV_RANK1 — Feature encoding addendum v1

Date: 2026-08-18
Status: frozen before any DEV_RANK1 COMEX predictive model is fit.

## Purpose

The frozen feature specification defines VWAP, POC, VAH/VAL and flow quantities, but does not fully specify how absolute auction prices enter a cross-year predictive model. Absolute GC price levels must not become accidental proxies for calendar era.

## Causal reference price

For any event/model cutoff, define `P_ref` as the last trade price of the selected active raw GC contract with `ts_event < floor_minute(cutoff)`.

If no such trade exists, price-relative B2 features are missing.

## Price-level encoding

Absolute local/session VWAP, POC, VAH and VAL are retained in audit output but do not enter the primary ridge model directly.

For any causal level `L`, the primary scalar is:

`distance_bps(L) = 10000 * (P_ref - L) / P_ref`.

Positive means the current causal GC price is above the level; negative means below.

Primary B2 price-level inputs are therefore:

- local VWAP distance for h = 1/5/15/30 minutes;
- current-session-to-date VWAP distance;
- local-30m POC / VAH / VAL distances;
- current-session-to-date POC / VAH / VAL distances.

No absolute GC POC/VWAP price is a primary predictor.

## Flow encoding

The primary model may use the raw frozen flow quantities because preprocessing is fit inside each training fold, plus explicitly scale-free versions already defined by the feature specification:

- A/B/N volume shares;
- normalized native delta `(BVol-AVol)/TotalVol`;
- robust delta sign.

Delta lower/upper bounds are retained in raw contracts; for diagnostics only, their shares of TotalVol may also be stored, but they are not a separately promoted feature family.

## Price-impact proxies

The frozen proxies are implemented literally on the active raw contract:

- `(last_trade_price - first_trade_price) / TotalVol`;
- `(last_trade_price - first_trade_price) / abs(native_delta)` when denominator > 0.

They are explicitly labeled proxies and never interpreted as direct passive-book absorption.

## HVN/LVN/voids

The v1 fixed definitions remain valid for auction construction and COMEX-native-zone generation.

However, because a profile can contain multiple HVNs/LVNs/void edges and the preregistration does not define a unique scalar event-level encoding, these secondary structures are **not included in the first primary B2 ridge comparison**. They may be reported descriptively and used in the separately preregistered native-zone study. Any later scalar encoding is exploratory unless frozen before DEV_RANK2; DEV_RANK2 cannot confirm an encoding invented after its data are opened.

## Missingness

No forward fill across session or contract boundaries. Model preprocessing uses training-fold-only imputation and explicit missing indicators. QA status labels themselves are not free trading filters.

## No outcome dependency

This encoding was fixed from scale invariance and causal reproducibility before fitting reaction or behavior models on DEV_RANK1 COMEX features.
