# US100 V17 14-Branch — FTMO MT5 F1

## Status

**Forward / Free-Trial candidate only.** This is the native-MT5 implementation of the causal V17 branch portfolio selected from the frozen 12-model engine. It is **not authorised for a paid FTMO Challenge until the FTMO-native parity checks below are completed**.

The EA uses only the chart/broker data available inside MT5 for the attached symbol. It makes no CME, Databento, WebRequest, DLL, API, or other paid/external market-data call.

## Files

- `US100_V17_14BRANCH_FTMO_F1.mq5`
- `US100_V17_Core.mqh`
- `US100_V17_Features.mqh`
- `US100_V17_Signals.mqh`
- `US100_V17_Execution.mqh`

Keep the five files in the same MT5 `MQL5/Experts` folder.

Default risk is **fixed USD 70 per trade on a 10k test account**. This matches V17/V19 (`0.70%` of the initial 10k); it is intentionally not compounded from current equity.

## Frozen V17 branches

- `ema_rev` LONG
- `kalman_mom` LONG + SHORT
- `open_drive` LONG
- `ou_lunch` LONG + SHORT
- `ou_rev` LONG
- `pd_rev` LONG
- `pm_mom` LONG + SHORT
- `sweep` SHORT
- `trend` LONG
- `vwap_rev` SHORT
- `vwap_scalp` LONG

No Tuesday/day-of-week filter and no additional session filter are applied. The source model's own time/day/regime filters remain in force.

## Execution design

- Attach to **FTMO `US100.cash`** (or the exact current FTMO Nasdaq symbol) and use M1 history.
- Signal calculations use closed M1 bars; the EA evaluates at the first tick of the next M1 bar, matching the frozen next-bar-open design as closely as possible in live MT5.
- At most one position controlled by this Magic Number can be open at once.
- Raw model daily quotas are reconstructed before branch filtering, including shadow generation of excluded BUY/SELL directions when they can consume a model quota.
- Branch filtering occurs before conflict resolution.
- Conflict resolution is strictly causal: same-bar priority/RR winner, then a 3-bar cooldown. The OU quality filter is applied after the conflict decision, so a rejected OU signal still consumes the conflict cooldown, as in the causal research engine.
- ATR5 × 0.80 hybrid stop widening, logical 0.25-point model rounding, actual-fill risk/RR revalidation, model BE/trailing/time-stop settings, 2R daily win cap and 10-loss cooldown are implemented.
- Position size is calculated with MT5 `OrderCalcProfit` against the intended stop. A post-fill safety check closes the trade if actual SL risk exceeds intended risk by more than the configured tolerance (2% by default).
- Internal protection state is persisted with MT5 terminal Global Variables so an EA/terminal restart can resume management of its own open trade.

## Clock

Research mapping is frozen at:

`FTMO/server time = New York time + 7 hours`

Default `InpServerToNYHours = 7`.

**Verify the current FTMO server clock before the first forward run.** If the broker clock mapping changes, change this input before starting the test; do not change strategy windows individually.

## First installation / QA

1. Open an FTMO **Free Trial 10k USD / MT5**. Do not use the paid Gold Challenge for this test.
2. In MetaTrader: `File -> Open Data Folder -> MQL5 -> Experts` and place the five V17 files there.
3. Open `US100_V17_14BRANCH_FTMO_F1.mq5` in MetaEditor and compile. Required gate: **0 compile errors**. This repository environment does not contain MetaEditor, so compilation has not been falsely claimed here.
4. In Strategy Tester, select the actual FTMO Nasdaq symbol (`US100.cash` if that is its exact name), M1, and **Every tick based on real ticks** when available. No optimisation.
5. Start with the defaults, especially `InpRiskDollars=70` and `InpServerToNYHours=7`.
6. Run a native-history test first, then a Free-Trial forward run. Do not retune model thresholds after seeing the Free-Trial outcome.

## What must be checked before a paid Challenge

The key gate is not whether the Free Trial happens to make +10%. We need to compare FTMO-native behaviour with the research implementation:

- signal timestamps and branch names;
- BUY/SELL direction;
- signal stop and target;
- actual spread at signal/fill;
- actual fill and slippage;
- number of signals/trades per day;
- risk dollars after FTMO volume-step rounding;
- BE/trailing/time-stop behaviour;
- cumulative R / P&L and drawdown.

The EA writes a common-file CSV log named:

`US100_V17_14BRANCH_FTMO_F1.csv`

## Important parity limitation

The research history was a free USTEC CFD dataset, not FTMO's own historical `US100.cash` quotes. The EA therefore represents a **prospective FTMO-native remeasurement**, not proof that FTMO fills will reproduce the historical results.

The daily EMA20/EMA50 regime is rebuilt from a 420-day M5 lookback by default. This is more than enough for live convergence, but a Strategy Tester run beginning very early in the historical sample may not be bit-identical to the research engine's full-history EMA initialisation. The forward FTMO period is the decisive parity check.

## Research checkpoint

V17 selected the 14-branch causal portfolio at fixed $70 risk. V19's severe historical stress (`STRESS`, 20-session blocks, `-1.5R` floating probe) passed the preregistered Free-Trial gates. Those simulations do **not** mean a literal ~99% real-world probability of passing FTMO; they justify a zero-cost Free Trial, nothing more.
