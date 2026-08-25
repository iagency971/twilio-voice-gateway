# E-BUY reaction DEV v1.0 — Addendum A: execution/target timing

**Frozen:** 2026-08-25 before the E-BUY coverage OOS result and before any reaction outcome is opened.

This addendum clarifies timing only; it does not alter the frozen trigger set or selection rule.

For `RECLAIM_CENTER`, `RECLAIM_FULL`, and `BULL_REJECTION`:

- the trigger becomes known at the confirming M1 close;
- hypothetical execution is the next available M1 open;
- the trigger is counted as `FIRED` only if that execution occurs before 17:00 NY, before zone invalidation, and **before TP1 has already been reached**;
- if TP1 lower boundary was touched at any time from the first E-BUY contact through the trigger-confirmation bar, classify that trigger episode as `TARGET_ALREADY_REACHED_BEFORE_TRIGGER`, not as a fired entry;
- if the next-open execution reference is at/above the frozen TP1 lower boundary, likewise classify it as `TARGET_ALREADY_REACHED_BEFORE_TRIGGER`.

For `TOUCH_REF`, execution reference remains the contact-state zhi at first contact.

First-passage barriers for each fired trigger are anchored to that trigger's own execution reference and use `v_contact` frozen at the first E-BUY contact.

For a confirmation trigger, path outcomes begin with the execution M1 bar. For `TOUCH_REF`, the contact M1 is included, but if both favorable and adverse barriers are contained in that same contact M1 bar the first-passage contest is `AMBIGUOUS` because intrabar order is unknown.

`TP1_BEFORE_INVALIDATION_US_END` is evaluated only after the trigger's execution reference. A TP1 touch that occurred before a confirmation-trigger execution cannot be credited to that trigger.