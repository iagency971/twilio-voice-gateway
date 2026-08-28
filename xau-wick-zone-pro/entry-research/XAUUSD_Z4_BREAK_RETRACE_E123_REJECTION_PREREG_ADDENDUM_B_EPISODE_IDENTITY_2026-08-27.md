# Addendum B — main-zone episode identity and next-open execution edge cases

Parent prereg: `XAUUSD_Z4_BREAK_RETRACE_E123_REJECTION_PREREG_v1_0_2026-08-27.md`
Date: 2026-08-27

Frozen before outcome execution.

## Active same-zone re-break

While a main-Z4 breakout episode is still active, a later close back above the same structural Z4 does **not** create a second episode. It is part of the existing breakout/retrace sequence.

A candidate Z4 is considered the same structural zone as an active episode when its interval overlaps the frozen main interval, or its center is within `0.25 * max(v_breakout, v_current)` of the active main center.

Once the prior episode has terminated, a later genuinely new upward crossing may create a new episode.

## Next-open execution

The bullish rejection is confirmed at M1 close and execution is the next M1 open.

No execution occurs when:
- there is no next M1 bar before 17:00 New York;
- next open is at or above frozen `target_zlo`;
- next open is at or below frozen `main_zlo`.

These are reported as non-execution edge cases, not losses.

## Outcome ordering

On an executed trade, each M1 bar is classified from observable OHLC only:
- high >= target_zlo and close < main_zlo on same bar => AMBIGUOUS;
- target only => TP_FIRST;
- close invalidation only => INVALIDATION_FIRST.

No assumed intrabar path is used.
