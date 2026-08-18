# XAUUSD Reaction Zone Research — Phase C Decision Gate v1

Frozen before reading the corrected 2011–2025 Phase-C multiyear aggregate.

## Purpose

Phase A established whether a zone family changes the conditional probability of a price reaction. Phase C asks a different question: whether a causal execution rule converts that information into positive trade expectancy after executable BID/ASK and costs.

No RR point is considered final merely because it is the maximum of the tested surface.

## Entry models under the v1 benchmark

- PASSIVE_TOUCH
- TOUCH_NEXT_OPEN
- CLEAN_REJECTION
- FAILED_AUCTION
- ACCEPTANCE_RETEST

The preregistered R2 RECLAIM_PULLBACK is evaluated separately in entries_v2 and cannot retroactively alter the v1 benchmark.

## Fixed target surface

0.5R, 1.0R, 1.5R, 2.0R, 2.5R, 3.0R.

## Execution / cost assumptions

- executable Dukascopy BID/ASK OHLC, not mid-price fills;
- structural stop with causal buffer `max(2 × contemporaneous spread, 0.10 × causal sigma60)`;
- ambiguous M1 TP+SL resolution is adverse: SL wins;
- intrabar limit-fill minute cannot claim a target that may have occurred before the fill;
- $22 round-turn per 100 oz broker lot sensitivity plus 1.5× cost stress ($33).

## Survival gate for further research

A family × entry-model × target-R cell survives Phase C only if all of the following hold on the unchanged 2011–2025 annual panel:

1. at least 300 trades in total;
2. weighted average net R after $22 RT > 0;
3. annual median net R after $22 RT > 0;
4. at least 10 of 15 annual windows have positive net R after $22 RT;
5. weighted average net R remains > 0 under the 1.5× cost stress;
6. at least 8 of 15 annual windows remain positive under 1.5× costs;
7. median annual PF net is > 1.0.

Passing this gate only means **candidate survives**. It is not a profitability validation.

## Final-strategy gates remain stricter

Later, after feature selection is frozen and evaluated on independent chronology / prospective data, the intended final governance remains approximately:

- >= 300 trades;
- PF net >= 1.25;
- average net expectancy >= +0.10R;
- positive under 1.5× costs;
- broad temporal stability;
- concentration / best-trades stress checks;
- anti-overfit diagnostics;
- independent feed / COMEX replication where applicable;
- prospective forward validation after final freeze.

## Multiple-testing rule

The six R targets constitute a response surface. A passing point may nominate a region for later validation, but the highest point is not automatically selected as the final RR. Isolated one-bin peaks are treated as suspect; neighboring RR behavior and annual stability must be inspected.
