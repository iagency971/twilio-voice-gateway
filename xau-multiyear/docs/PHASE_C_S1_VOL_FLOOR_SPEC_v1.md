# XAUUSD Reaction Zone Research — Phase C S1 Volatility-Floor Stop Spec v1

Frozen after observing that the preregistered structural-stop baseline does not automatically convert Phase-A zone reaction edge into net trade expectancy, but **before running any S1 results**.

## Scientific status
S1 was already part of the conceptual research plan as the volatility-normalized stop family. The exact grid below was not previously frozen; therefore S1 is a **new exploratory sensitivity** and cannot be treated as virgin confirmation. Any surviving cell must later be revalidated on independent chronology / prospective data.

## Entry models
Use the unchanged Phase-C v1 causal entries: PASSIVE_TOUCH, TOUCH_NEXT_OPEN, CLEAN_REJECTION, FAILED_AUCTION, ACCEPTANCE_RETEST. R2 RECLAIM_PULLBACK remains separate.

## S1 volatility floor
Build the entry and structural stop exactly as entries_v1.py does. Let `risk_struct = abs(entry - structural_stop)` and `sigma60` be the causal robust one-hour volatility scale known at contact.

For each fixed multiplier `k ∈ {0.25, 0.50, 0.75, 1.00}` set `risk_S1 = max(risk_struct, k * sigma60)`.

LONG: `stop_S1 = entry - risk_S1`. SHORT: `stop_S1 = entry + risk_S1`.
Thus S1 can only widen a structural stop; it can never move the stop inside the original structural invalidation.

## Targets
Keep the unchanged fixed-R surface: `R ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}`. No k/R pair is selected in advance.

## Execution / costs
Identical to Phase C v1: Dukascopy executable BID/ASK; adverse same-M1 TP/SL ambiguity; no pre-fill target credit on intrabar limit fills; stop gaps worsened; $22 RT/100oz sensitivity and $33 stress.

## 2025 computational screen before multi-year
Retain the full 4×6 stop/target surface. A cell is only worth sending to 2011–2025 if: >=300 trades; net expectancy after $22 >0; net expectancy under $33 not worse than -0.02R; and at least one adjacent R or adjacent k cell has non-negative net expectancy after $22. This is a screen, not validation.

## Multi-year gate
If promoted, use the frozen Phase-C survival gate: >=300 total trades, positive weighted and annual-median net R, >=10/15 positive years after $22, positive under 1.5x costs with >=8/15 positive years, median annual PF >1.
