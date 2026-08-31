# XAUUSD Z4 corridor retrace V3 — Addendum A: exact causal and execution rules

**Date:** 2026-08-31  
**Status:** PREOUTCOME / authoritative clarification  
**Parent preregistration:** `XAUUSD_Z4_CORRIDOR_RETRACE_LEVEL_REACTION_V3_PREREG_2026-08-31.md`

This addendum resolves implementation ambiguities before any V3 reaction outcome is opened. It does not change the research question or use any V3 outcome.

## A1. Active structural episode authority

The frozen legacy structural engine may have more than one active MAIN→TARGET episode at the same M1.

For V3, every raw M1 belongs to at most one **authority corridor** for candidate birth/contact:

1. among active valid episodes, choose the episode with greatest frozen `main_zhi`;
2. tie-break by most recent `breakout_time`;
3. final tie-break by smallest deterministic `episode_id`.

Only candidates and controls belonging to that authority episode may register a contact on that M1. This prevents one price bar from being counted multiple times through overlapping corridors.

## A2. BROKEN_PIVOT_HIGH memory

A confirmed pivot high may predate the MAIN breakout because resistance-to-support requires a prior resistance level.

At the bar that arms the candidate by closing strictly above the pivot level:

- the pivot confirmation bar must be within the preceding **240 available M1 bars**;
- pivot confirmation still requires two completed bars to the right;
- the arming close must occur after the MAIN breakout;
- candidate level must be strictly inside the current frozen authority corridor.

The 240-bar memory is fixed and may not be tuned after outcomes.

## A3. Post-break-only families

`POST_BREAK_PIVOT_LOW` and `BULL_FVG_MID` must be created from formations whose defining final bar occurs strictly after the MAIN breakout.

No pre-break pivot low or pre-break FVG may be imported into these two families.

## A4. Dynamic candidate clustering

Clustering is causal and deterministic.

For every newly available raw candidate in the current authority episode:

1. compare it only with currently uncontacted clusters in that episode;
2. two raw candidates are linked if their levels differ by at most `0.10 * min(v_birth_a, v_birth_b)`;
3. clustering uses connected components of this symmetric link relation;
4. cluster center = median of current member levels;
5. cluster birth = latest member availability/arming time;
6. cluster `v_birth` = causal volatility at that latest birth time;
7. family set = sorted unique member families;
8. confluence count = number of distinct families.

When a new member changes an uncontacted cluster:

- the cluster center and birth are recomputed;
- all previously generated neutral controls for that cluster are invalidated;
- new controls are generated from the updated center and updated `v_birth`;
- no bar at or before the updated birth can be a contact.

After the first eligible contact, the cluster is permanently closed. A later nearby raw candidate may form a new cluster but cannot rewrite the contacted cluster.

## A5. Exact contact ordering

A candidate/control contact requires `contact_time > birth_time`.

Within one M1 authority corridor update, termination precedence is:

1. if the frozen TARGET is reached on the bar, no new candidate/control contact is registered on that bar;
2. else if the M1 close is strictly below frozen `main_zlo`, no new contact is registered and the episode terminates;
3. else candidate/control contacts are evaluated;
4. new candidate births from that same closing bar become available only after the close and therefore cannot also contact on that bar.

This is fail-closed against same-bar lookahead.

## A6. Neutral-control availability

Controls are regenerated whenever an uncontacted cluster is updated as described in A4.

At control generation time, the `{-0.50, -0.25, +0.25, +0.50} * v_birth` pseudo-levels are checked against all candidate clusters causally available at that time, including the newly updated cluster.

A control that later becomes close to a newly born structural candidate is **not retrospectively removed**. Future structural information cannot rewrite a control chosen earlier.

## A7. Exact primary reaction label

At candidate/control contact bar close:

- anchor = contact close;
- `v0` = causal authority-corridor volatility available for that contact bar;
- contact bar high/low are excluded;
- scan the next 10 available M1 bars in the same NY session;
- favorable = anchor + `0.50*v0`;
- adverse = anchor - `0.50*v0`;
- if both favorable and adverse are touched in the same scanned M1, label 0;
- if adverse first, label 0;
- if favorable first, label 1;
- if neither, label 0.

MAIN/TARGET termination is descriptive for this short reaction endpoint; it does not censor the symmetric 10-bar reaction scan except at the NY session boundary. This avoids outcome-dependent censoring.

## A8. Exact executable entry labels

All execution modes require the structural episode still valid at the signal close and a next M1 open in the same US session.

If the signal bar reaches TARGET or closes below MAIN, there is no entry.

At the actual next-open entry:

- if entry open is at/above `target_zlo`, no entry;
- if entry open is at/below `main_zlo`, no entry.

### TOUCH_NEXT_OPEN

Signal close = contact bar close. Entry = immediately following M1 open.

### CONTACT_RECLAIM_NEXT_OPEN

Same timing as TOUCH, but contact close must be strictly above candidate level.

### CONTACT_BULL_RECLAIM_NEXT_OPEN

Same timing as TOUCH, but contact close must satisfy both `close > open` and `close > candidate_level`.

### ONE_BAR_FIRST_BULL_RECLAIM

Used only when CONTACT_BULL_RECLAIM did not fire.

- inspect exactly the immediately following completed M1;
- it must not reach TARGET or close below MAIN;
- it must satisfy `close > open` and `close > candidate_level`;
- entry = the next M1 open after that qualifying bar;
- no second waiting bar is allowed.

## A9. Exact post-entry reaction outcome

For each executed mode:

- entry anchor = actual entry M1 open;
- use contact `v0` unchanged;
- favorable = entry + `0.50*v0`;
- adverse = entry - `0.50*v0`;
- scan up to 10 available M1 bars **starting with the entry bar**, because the trade is assumed entered at that bar's open;
- both touched in one M1 = conservative failure 0;
- favorable first = 1; adverse first/neither = 0;
- truncate only at 17:00 NY.

## A10. Exact latency-loss metric

For TOUCH/CONTACT_RECLAIM/CONTACT_BULL_RECLAIM, no completed post-contact bar exists before the next-open entry, so `move_completed_before_entry = false` by construction; contact-bar high is not used.

For ONE_BAR_FIRST_BULL_RECLAIM:

- inspect only the one completed qualification bar between contact and entry;
- `move_completed_before_entry = true` if its high reached `contact_close + 0.50*v0`;
- entry drift = `(entry_open - candidate_level)/v0`.

The VAL execution-usefulness gate is applied exactly as preregistered: median entry drift <=0.25v and missed primary-success share <20%.

## A11. DEV continuation gate tightened before outcomes

DEV may open VAL only if the **pooled matched structural-level location test** satisfies all mandatory DEV quality gates **and**:

- point matched effect >0;
- 95% bootstrap lower bound >0.

A weak positive DEV point estimate with an interval crossing zero is not sufficient to spend VAL.

## A12. REP continuation and final confirmation

REP 2023 opens only if:

1. pooled VAL location PASS is true; and
2. at least one low-latency execution mode passes every VAL execution-usefulness gate.

In REP, final pooled location confirmation requires the same direction and uncertainty standard:

- mandatory sample/quality gates;
- matched effect >0;
- bootstrap 95% lower bound >0.

A production-eligible execution mode must also repeat its complete VAL usefulness gate in REP without any refit or threshold change.

No DEV/VAL family diagnostic can change the pooled candidate definition before REP.
