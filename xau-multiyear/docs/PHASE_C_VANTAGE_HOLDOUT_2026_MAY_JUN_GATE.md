# Phase C Vantage RAW — May–June 2026 temporal holdout gate

Frozen after the completed 2011–2025 corrected Vantage RAW multiyear gate and before reading May–June 2026 P&L for its survivors.

## Status of the window

Target window: `2026-05-01T00:00:00Z` to `2026-06-30T00:00:00Z` (June 30 retained as post-window data for the 120-minute horizon). Twelve months of causal warm-up are included before the target window.

This is a temporal P&L confirmation window for the corrected Vantage execution model, not a fully virgin market-research OOS block: 2026 prices were previously inspected for zone-reaction research. However, the corrected Vantage RAW P&L of the eight 2011–2025 survivors was not used to select or tune them on this target window.

## Frozen survivors entering the holdout

No additional cells may be promoted from the holdout.

1. `DOZ_OBJECTIVE_ONLY + CLEAN_REJECTION + STRUCTURAL`, target R = 0.5
2. same, target R = 1.0
3. same, target R = 1.5
4. same, target R = 2.0
5. same, target R = 2.5
6. same, target R = 3.0
7. `DOZ_OBJECTIVE_ONLY + TOUCH_NEXT_OPEN + VOL_FLOOR_0.50`, k=0.50, target R = 2.5
8. `DOZ_OBJECTIVE_ONLY + TOUCH_NEXT_OPEN + VOL_FLOOR_0.75`, k=0.75, target R = 3.0

## Execution scenarios (unchanged)

- Primary: fixed spread 0.11 USD + 6 USD round-turn commission per 100oz lot.
- Sensitivity: 0.10 USD + 6 USD.
- Sensitivity: 0.12 USD + 6 USD.
- Stress: 0.18 USD + 9 USD.

## Holdout interpretation rules

The six-cell CLEAN_REJECTION RR plateau is evaluated as a family, not by selecting the best holdout RR.

A. Primary consistency: at least 4 of the 6 CLEAN_REJECTION RR cells must have positive net R in the primary scenario, and the median net R across the six RR cells must be positive.

B. Stress consistency: at least 3 of the 6 CLEAN_REJECTION RR cells must remain positive under the stress scenario, and the median stress net R across the six cells must be non-negative.

C. Trade-count disclosure: holdout trade count is reported for every cell. No strong statistical claim is made if the CLEAN_REJECTION sample contains fewer than 20 trades.

D. The two TOUCH_NEXT_OPEN cells are reported individually. They are confirmatory only if their primary net R is positive; stress sign is reported but is not used to rescue or reject the CLEAN_REJECTION family.

E. No new RR, stop, entry, session filter, subtype filter, breakeven, trailing, partial exit, or cost scenario may be introduced from this holdout.

Passing this temporal gate still does not establish live profitability. Remaining requirements include COMEX incremental-value testing, broker-feed replication, and genuinely prospective validation after the full specification is frozen.