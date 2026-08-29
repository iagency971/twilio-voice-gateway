# XAUUSD — E intrinsic reaction outcome preregistration V1

**Frozen before outcome opening:** 2026-08-29  
**Scope:** XAUUSD M1 BUY, US 08:00–17:00 `America/New_York`  
**Depends on:** `E_INTRINSIC_SNAPSHOT_V1_REAL_QA_PASS`  
**Trading/P&L interpretation:** prohibited in this study.

## 1. Primary population

One E episode per NY session, evaluated at its **first armed contact** only.

An episode is armed after a confirmed M1 close strictly above the episode's `zhi`. The primary contact is the first subsequent M1 bar whose range intersects `[zlo,zhi]`, before 17:00 New York.

The feature vector used for that episode is the last confirmed `E_INTRINSIC_SNAPSHOT_V1` row strictly earlier than the contact time. If no such snapshot exists, the episode is excluded with reason `NO_PRECONTACT_INTRINSIC_SNAPSHOT`.

For the intrinsic-model population, that snapshot must also satisfy `current_family != Z4` and `origin_family != Z4`; otherwise exclude with reason `Z4_CONTEXT_ONLY_NOT_INTRINSIC_V1`.

At that snapshot freeze:

- `zlo0`, `zhi0`, `center0` are frozen;
- `v0 = v_snapshot` is frozen;
- the V1 intrinsic features are frozen.

No value is updated after contact.

## 2. Primary reaction outcome

Observation window: from the contact bar through the next 30 completed M1 bars, truncated at 17:00 New York.

Favorable reaction level:

`F = zhi0 + 0.50 * v0`

Structural invalidation:

first confirmed M1 close strictly below `zlo0`.

Classification:

- `FAVORABLE_FIRST`: favorable level is reached before invalidation;
- `INVALIDATION_FIRST`: invalidation occurs before favorable level;
- `AMBIGUOUS_SAME_BAR`: favorable level is touched and the same M1 bar closes below `zlo0`, with intrabar ordering unknowable from M1;
- `NEITHER`: no favorable-first event before invalidation/window/session end.

### Primary binary label

- `1` for `FAVORABLE_FIRST`;
- `0` for `INVALIDATION_FIRST`, `AMBIGUOUS_SAME_BAR`, and `NEITHER`.

This conservative treatment is frozen before outcomes. `AMBIGUOUS_SAME_BAR` must also be reported separately.

## 3. Secondary outcomes — descriptive only

Pre-specified secondary diagnostics:

- MFE normalized by `v0` at W5, W15, W30, W60 where available before session end;
- MAE normalized by `v0` at W5, W15, W30, W60;
- time to favorable level;
- survival without confirmed close below `zlo0` at W5/W15/W30/W60;
- maximum penetration depth relative to frozen zone width;
- ambiguity rate.

No secondary outcome may replace the primary binary outcome because it appears more favorable.

## 4. Retests

Retests are not part of the primary population. They may be kept in a separate repeated-measures ledger after the primary analysis has been frozen and reported, but cannot alter the primary verdict.

## 5. Prohibited analyses before model freeze

No scan over alternative favorable multipliers, time windows, arm rules, invalidation rules, sessions, directions, E ranks or Z4 geometry may be used to choose a better-looking primary definition.
