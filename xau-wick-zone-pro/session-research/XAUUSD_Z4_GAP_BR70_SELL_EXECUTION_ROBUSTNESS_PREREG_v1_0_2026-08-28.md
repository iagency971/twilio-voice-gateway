# XAUUSD standalone Z4-gap BR70 SELL — execution robustness prereg v1.0

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`
Status: **FROZEN BEFORE SESSION-END LIQUIDATION / COST RESULTS**

## Scientific status

This is an execution robustness diagnostic applied after the standalone Z4-gap BR70 SELL gross structural study. It cannot create validation and cannot be used to optimize signal selection.

Frozen trade ledger source: workflow run `33203080123`, generated under `XAUUSD_Z4_GAP_BR70_DIRECT_SELL_PREREG_v1_0_2026-08-28.md` (blob `8358749cab0a4cef1cc5afc429e3b72fd665b86a`).

No trade may be added, removed or reclassified by any market outcome or cost result.

## Full realized gross-R ledger

Every executed trade receives a realized gross R:

- `TP_FIRST`: `+nominal_rr`;
- `INVALIDATION_FIRST`: `-1`;
- `NEITHER`: liquidate at the BID M1 close recorded at the frozen `outcome_time` (session end), with gross SELL R = `(entry_price - session_end_close) / (stop_price - entry_price)`;
- `AMBIGUOUS`: conservative worst-case `-1`.

The exact hash-verified BID M1 source used by prior studies is reused to recover the session-end close. There is no extension beyond the frozen same-session horizon.

## Effective transaction-cost sensitivity

Rather than assume a broker-specific constant spread, evaluate total round-trip execution cost as an equivalent XAUUSD price cost in USD per ounce. This cost is intended to combine spread + commission-equivalent + slippage.

Frozen grid, applied identically to every trade:

`0.00, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50 USD/oz`.

For each cost `c`:

`net_R = gross_realized_R - c / (stop_price - entry_price)`.

No cost-dependent filtering is allowed.

Also report the algebraic break-even effective cost:

`break_even_cost_usd_per_oz = mean(gross_realized_R) / mean(1 / stop_distance_usd)`

when the denominator is positive.

## Windows and sessions

Same frozen windows and sessions:
- H1: 2024-08-01 to 2025-08-01 UTC;
- H2: 2025-08-01 to 2026-08-01 UTC;
- US 08-17 NY;
- Asia broad 18-03 NY;
- Asia Core standalone 21-03 NY;
- Europe 03-08 NY.

## Outputs

For each session and H1/H2, and pooled by all trades:
- N executed;
- mean gross realized R including session-end liquidation and conservative ambiguous handling;
- distribution of session-end `NEITHER` realized R;
- mean net R for each frozen cost grid value;
- break-even effective USD/oz cost;
- same results under the pre-existing deterministic one-position-at-a-time selection (next entry only after prior selected trade's frozen outcome_time).

No optimization, no new production gate. Interpretation is descriptive execution feasibility only.

Production authorization: **NONE_EXECUTION_ROBUSTNESS_ONLY**.
