# XAUUSD Reaction Zones — COMEX DEV_RANK1 Feature Specification CANONICAL v1.1

Date: 2026-08-18
Status: canonical pre-acquisition amendment.

This file **supersedes the session/time conventions in** `COMEX_DEV_RANK1_FEATURE_SPEC_v1.md`. All formulas and restrictions in v1 remain in force unless explicitly replaced below. In any conflict, this v1.1 file controls.

## Reason for amendment

The paid 12-session pilot shows a real historical change in GC trading hours:

- 2011/2013/2015 pilot sessions contain GC trades through approximately 17:15 New York time, followed by a ~45-minute break and reopening at 18:00;
- 2017+ pilot sessions trade through approximately 17:00 New York time and reopen at 18:00.

This is consistent with CME's published September 2015 Globex maintenance change for COMEX/NYMEX. The research must not force a 17:00 boundary onto earlier years.

## Canonical GC auction-session definition

All times use `America/New_York`, with DST handled by the timezone database.

### Before trade date 2015-09-21

GC auction session for research date D:

- start: D-1 at 18:00 New York time;
- end: D at 17:15 New York time, end-exclusive for feature construction.

The 17:15–18:00 interval is outside the auction session.

### From trade date 2015-09-21 onward

GC auction session for research date D:

- start: D-1 at 18:00 New York time;
- end: D at 17:00 New York time, end-exclusive.

The 17:00–18:00 interval is outside the auction session.

Holiday/early-close sessions are **not stretched** to synthetic full length. Their actual records inside the scheduled session are used, with an explicit `short_session` / availability QA flag.

## Distinguish XAU research date from GC auction session

The existing XAU event engine may continue to use its frozen 17:00 New York `research_trading_date` key for XAU stratification and matching.

GC session-state features do **not** use that key to decide which GC trades belong to a completed or developing auction profile before 2015-09-21.

Each XAU event is linked to the GC auction session containing its causal decision timestamp. If the timestamp falls inside the daily GC maintenance break, session-to-date auction features are unavailable and receive an explicit missing/maintenance flag.

## Acquisition envelope

The existing wide Databento request envelope — previous local 17:00 through current local 18:00 — is retained for acquisition because it safely contains both historical session regimes.

Raw records outside the canonical GC auction-session interval are preserved for QA but excluded from that session's VWAP/CVD/profile calculations.

## Session-to-date features

The following v1 features now reset at the canonical GC auction-session start defined above:

- session VWAP;
- native CVD and its uncertainty bounds;
- session volume/trade count;
- developing volume-at-price profile;
- developing POC/VAH/VAL/HVN/LVN/void state;
- session-relative elapsed time.

They also reset at any continuous-contract `instrument_id` mapping change.

## Completed prior-session features

A prior-session VWAP/profile is considered known only after the relevant canonical session end:

- 17:15 New York before 2015-09-21;
- 17:00 New York on/after 2015-09-21.

A level from a completed prior session cannot be used before that timestamp.

## Relative-volume seasonality

The v1 relative-volume baseline is amended to use **minute offset from canonical GC auction-session start**, not offset from a fixed 17:00 research-day boundary.

For each horizon h:

1. determine current minute offset from canonical GC session start;
2. retrieve the same offset/window from up to the previous 20 valid GC auction sessions under their own era-appropriate session definitions;
3. baseline = median volume of those prior windows;
4. require at least 10 valid prior sessions;
5. never use future sessions.

Holiday/short sessions that do not contain the required offset do not contribute to that baseline.

## Pilot validation rule

The pilot maintenance-gap observations are QA evidence only. They do not select trading features or thresholds. The historical cutoff date comes from the documented exchange-hours change, not from profitability or reaction outcomes.

## Canonical status

For DEV_RANK1, the effective feature specification is:

1. `COMEX_DEV_RANK1_FEATURE_SPEC_v1.md`, plus
2. this `COMEX_DEV_RANK1_FEATURE_SPEC_CANONICAL_v1_1.md`, which overrides session/time definitions.

No further session-definition change is permitted after DEV_RANK1 market-data acquisition unless documented as a protocol deviation; such a deviation cannot be validated using DEV_RANK2 as if it were preregistered.
