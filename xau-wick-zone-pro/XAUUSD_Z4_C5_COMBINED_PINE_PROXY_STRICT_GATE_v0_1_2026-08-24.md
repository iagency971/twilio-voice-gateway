# XAUUSD Z4 C5 — strict combined Pine-proxy parity gate v0.1

**Date:** 2026-08-24  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Status:** FROZEN BEFORE C5 COMBINED-PARITY RESULT IS READ  
**Future outcomes used:** NONE

## Purpose

The generic comparator currently present in the repository contains later, more permissive engineering thresholds. Those thresholds are NOT authorized for the C5 promotion decision.

The C5 post-replication gate requires preservation of the historical C15 combined-proxy gate. Therefore the decision on C5 must be made from the reported metrics using the original strict thresholds that the C15 proxy actually passed.

## Frozen strict thresholds

All conditions must pass:

- exact-zone match rate >= **0.90**;
- proxy-zone match rate >= **0.90**;
- median IoU >= **0.80**;
- p10 IoU >= **0.55**;
- median center error <= **0.08 vseg**;
- p95 center error <= **0.25 vseg**;
- raw-score Pearson >= **0.98**;
- raw-score Spearman >= **0.98**;
- median absolute raw-score error <= **0.015**;
- p95 absolute raw-score error <= **0.060**;
- matched top-1 zone agreement >= **0.85**.

These are the thresholds recorded in `parity/XAUUSD_Z4_PINE_COMBINED_PARITY_RESULTS_v0_1.json` for the previously accepted C15 combined proxy.

## Decision rule

The C5 combined proxy is PASS only if every strict condition above is true. A PASS produced by the generic comparator's more permissive current `checks` object is insufficient by itself.

No threshold relaxation or metric substitution is allowed after the C5 result is read.

This gate is outcome-blind and does not authorize FOREXCOM transfer, reaction/reversal claims, execution rules, SL/TP/RR, or `VALIDATED_PROXY` before TradingView runtime QA.
