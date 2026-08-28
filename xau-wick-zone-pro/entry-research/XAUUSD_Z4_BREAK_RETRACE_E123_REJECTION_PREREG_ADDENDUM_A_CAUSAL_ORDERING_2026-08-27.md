# Addendum A — causal ordering / simultaneous structural episodes

Parent prereg: `XAUUSD_Z4_BREAK_RETRACE_E123_REJECTION_PREREG_v1_0_2026-08-27.md`
Date: 2026-08-27

Frozen before running the new setup outcome engine.

## C5 state availability

A Z4/E display state timestamped `t` is treated as known only after the M1 close at `t`.
It may therefore be used for decisions on M1 bars `(t, next_C5]`.

This matches the existing causal E-BUY reaction convention and prevents an M1 candle from creating/updating an E zone and simultaneously being counted as a historical rejection of that newly computed zone.

## Breakout crossing

For a main Z4 known at state `t`, a breakout is the first subsequent M1 close in `(t, next_C5]` that is strictly above its frozen `zhi`, provided the immediately preceding M1 close was not already above that same frozen `zhi`.

The breakout candle itself does not count as the required post-breakout retracement.

## Multiple Z4s crossed on the same M1 close

To avoid duplicating one market impulse into several near-identical trades, if one M1 candle newly closes above several eligible Z4 zones from the same causal state, retain only the crossed Z4 with the **highest `zhi`** as the main-zone breakout candidate.

Its target is the next higher Z4 from that same causal state.

## Concurrent active breakout episodes

More than one structural episode may exist later in the session if distinct breakouts occur at distinct times.

If a single E rejection candle would validly trigger more than one still-active main-Z4 episode, assign that rejection to the active episode with the **highest `main_zhi`** (nearest structural support from above). Ties use the most recent breakout time.

A given M1 rejection candle can therefore execute at most one trade.

## Target before entry

If price reaches the frozen target Z4 lower boundary at any time after breakout but before execution, the episode terminates as `TARGET_REACHED_BEFORE_ENTRY` and cannot later fire.

## Main-Z4 retracement

Only M1 bars strictly after the breakout candle can set `main_retrace_seen`.
The range must intersect `[main_zlo, main_zhi]`. A wick below `main_zlo` remains valid as long as that candle does not close below `main_zlo`.
