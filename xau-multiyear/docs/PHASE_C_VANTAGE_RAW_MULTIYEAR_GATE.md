# XAUUSD Reaction Zone Research — Vantage RAW multiyear decision gate

Frozen before reading the corrected Vantage RAW 2011–2025 aggregate.

## Execution scenarios

The research mid-price path and all Phase-A/Phase-B zone/contact definitions remain unchanged. Only executable BID/ASK and commission are overlaid.

- `S10_C6`: fixed spread 0.10 USD, commission 6 USD round-turn / 100 oz lot — sensitivity.
- `S11_C6_PRIMARY`: fixed spread 0.11 USD, commission 6 USD round-turn / 100 oz lot — primary.
- `S12_C6`: fixed spread 0.12 USD, commission 6 USD round-turn / 100 oz lot — sensitivity.
- `S18_C9_STRESS`: fixed spread 0.18 USD, commission 9 USD round-turn / 100 oz lot — stress.

The fixed-spread overlay is a broker-cost model, not a claim that Vantage spread is constant in live trading. It is based on the observed 0.10–0.12 USD range supplied for the user's account, with a deliberately wider stress case.

## Entry-model handling

- Phase-A and Phase-B are not recalculated/reselected.
- Structural entry models retain their existing definitions.
- Raw `TOUCH_NEXT_OPEN` without a risk floor is audit-only and excluded from strategy selection because Phase-C diagnostics found pathological near-zero structural risk.
- `TOUCH_NEXT_OPEN` is evaluated only with the already-frozen volatility-floor grid `k ∈ {0.25, 0.50, 0.75, 1.00}`, where `risk = max(structural_risk, k × causal_sigma60)`.
- Target surface remains `R ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}`. No new RR values are introduced.
- Same-bar TP/SL ambiguity remains adverse: SL wins.
- Horizon remains 120 minutes.

## Event parity gate

Before any multiyear interpretation, the corrected 2025 runner must reproduce exactly `80,617` Phase-B target events. If event count changes, the run is rejected because the broker overlay must not alter zone detection or behavior classification.

## Multiyear survival gate

A `sample × entry_model × risk_rule × target_R` cell survives only if all are true:

1. At least 300 trades across 2011–2025.
2. Weighted average net R in `S11_C6_PRIMARY` > 0.
3. Median annual net R in `S11_C6_PRIMARY` > 0.
4. At least 10 of 15 years positive in `S11_C6_PRIMARY`.
5. Median annual PF in `S11_C6_PRIMARY` > 1.0.
6. Weighted average net R in both `S10_C6` and `S12_C6` > 0.
7. Weighted average net R in `S18_C9_STRESS` > 0.
8. At least 8 of 15 years positive in `S18_C9_STRESS`.

Neighboring-R stability is inspected. A single isolated RR bin is not accepted merely because it is the maximum.

Passing this gate nominates a candidate for chronology/COMEX/broker/prospective validation. It is not a live-profitability validation.

## Scientific status

This is a correction of a previously miscalibrated broker-cost model. It does not reopen Phase A or Phase B, and it must not be used to retrospectively alter zone definitions after seeing Vantage-cost results.
