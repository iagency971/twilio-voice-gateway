# E-BUY reaction DEV v1.0 — Addendum B: runtime state propagation repair

**Frozen:** 2026-08-25 while the E-BUY coverage OOS replication v1.0 is still running and before any E-BUY reaction outcome has been computed or inspected.

## Reason for this addendum

Static review of the prepared reaction engine found an implementation defect before activation: `assign_episode_states()` precomputed the full sequence of display-state dictionaries before `detect_contacts()` ran. The later `ARMED` and `CONSUMED` mutations therefore affected only the current snapshot object and were not propagated into already-created state objects for subsequent C5 snapshots.

This is a software-state bug, not a scientific-rule change.

## Frozen repair

The reaction definitions, trigger set, target definition, H1/H2 split, barriers and selection rule remain unchanged.

The repaired implementation must:

- keep `display_episode_id` and geometry from the frozen sticky location engine exactly as before;
- maintain a separate runtime dictionary keyed by `display_episode_id` for `armed`, `arm_time`, `arm_close`, and `consumed`;
- carry that runtime state across every contiguous snapshot belonging to the same display episode;
- set `consumed = true` after the episode's first fresh contact and prevent any later contact from that display episode during that session;
- never use a future bar to set or repair runtime state;
- leave H2 reaction outcomes completely unopened.

The runtime state may be updated on causal pre-DEV snapshots needed for continuity, but contacts/triggers/outcomes are recorded only when the first contact is inside the frozen REACTION_DEV window.

No outcome has been viewed, so this repair is outcome-blind and does not alter preregistered selection criteria.
