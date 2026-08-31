# XAUUSD Z4 corridor retrace levels — V3 preregistration

**Date:** 2026-08-31  
**Mode:** Pro methodological freeze  
**Repository:** `iagency971/twilio-voice-gateway`  
**Branch:** `agent/xau-wick-zone-pro-dev`  
**Scope:** XAUUSD BID M1, BUY only, US 08:00–17:00 `America/New_York`

## 1. Research question

After an upward break of a causal main Z4 and before the next higher causal Z4, can price levels formed causally inside that corridor identify **better short-horizon BUY retracement reaction locations** than nearby neutral levels, and can the reaction be acted on with zero/one-bar confirmation rather than the legacy delayed `BR70` rule?

The study is deliberately about two separate things:

1. **Location edge:** does a structural intermediate level itself improve the probability of an early bullish reaction after first retracement contact?
2. **Execution latency:** once a valid level is touched, what is gained or lost by waiting for a minimal same-bar reclaim or one additional bullish bar?

A level is not useful merely because price revisits it. It must improve post-touch reaction relative to nearby neutral levels and remain actionable before the move is substantially gone.

## 2. Explicit exclusions from prior failed work

The V2 E-zone study is closed and non-confirmatory. Therefore:

- displayed E1/E2/E3 zones are **not candidate levels** in V3;
- the V2 E score, V1 E score, E family, E rank, E1/E2/E3 slot and all E thresholds are **forbidden predictors and filters**;
- no V2 rescue analysis is allowed;
- no `E>=x`, no `ABOVE_MAIN + E score`, and no post-hoc E subgroup may enter V3;
- `BR70` is **not** an entry rule and 0.70 is not treated as a privileged rejection threshold.

The validated Z4 program is reused only for **causal corridor anchors**. Prior Z4 work validates revisit information, not reaction after contact; V3 must independently establish reaction-location value.

## 3. Frozen structural episode

For each US session, using only causal state available before each M1 close:

1. Detect an upward break of a causal upper Z4 exactly as in frozen engine blob `7862638917015838948001a374f9bea7dba83e07`: previous M1 close is at/below the Z4 upper edge and current M1 close is strictly above it.
2. Freeze the crossed Z4 as `MAIN` (`main_zlo`, `main_center`, `main_zhi`).
3. Freeze the nearest higher causal Z4 as `TARGET`; target entry edge is `target_zlo`.
4. Define the open corridor as `(main_zhi, target_zlo)`.
5. If no higher Z4 exists, the episode is not eligible.
6. A close strictly below frozen `main_zlo` invalidates the episode. A wick below `main_zlo` does not.
7. A touch of `target_zlo` ends the episode for new entries.
8. No candidate level may be created from information after its first retracement contact.

The main and target Z4s are anchors only. They are not V3 candidate observations.

## 4. Causal intermediate candidate families

Only the following three candidate families are allowed. Definitions are fixed before outcomes.

### A. `BROKEN_PIVOT_HIGH` — resistance-to-support level

- A pivot high at M1 index `i` requires `high[i]` to be strictly greater than `high[i-2]`, `high[i-1]`, `high[i+1]`, and `high[i+2]`.
- It becomes causally confirmed only at the close of bar `i+2`.
- Candidate level = `high[i]`.
- It becomes armed only after a later M1 close is strictly above the level.
- At arming time the level must lie strictly inside the frozen corridor.
- Only the first later retracement contact from above is eligible.

### B. `POST_BREAK_PIVOT_LOW` — post-breakout support pivot

- Pivot low at index `i`: `low[i]` is strictly below `low[i-2]`, `low[i-1]`, `low[i+1]`, and `low[i+2]`.
- It is available only at close `i+2`.
- The pivot must occur after the MAIN breakout.
- Candidate level = `low[i]` and must lie strictly inside the corridor.
- It becomes armed after any later M1 close strictly above the level.
- Only the first later retracement contact from above is eligible.

### C. `BULL_FVG_MID` — midpoint of a causal bullish three-bar gap

- At bar `i`, a bullish gap exists if `low[i] > high[i-2]` using completed M1 bars only.
- The gap is available at close of bar `i`.
- Frozen gap = `[high[i-2], low[i]]`.
- Candidate level = arithmetic midpoint `(high[i-2] + low[i]) / 2`.
- The midpoint must lie strictly inside the frozen corridor.
- It is armed at availability because the completed bar already lies above the frozen gap.
- Only the first later retracement contact from above is eligible.

No Fibonacci levels, round numbers, order-block labels, E-derived levels, hand-drawn levels or outcome-selected thresholds are allowed in V3.

## 5. Deterministic candidate de-duplication

Within one structural episode, if two candidate levels are separated by at most `0.10 * v_birth`, they belong to the same local structural cluster.

The cluster representation is frozen as:

- center = median of member levels;
- birth time = latest member availability time, so all member evidence is causal;
- `candidate_family_set` = sorted unique family names;
- `confluence_count` = number of distinct families in the cluster;
- no family receives priority because of outcomes.

A cluster is a point level for the primary test; its member span is descriptive only and does not change the touch rule.

## 6. Contact rule

After candidate birth/arming:

- contact is the first later M1 whose range contains the frozen candidate level: `low <= level <= high`;
- contact must occur while MAIN is not close-invalidated and before TARGET is reached;
- contact bar must be in the same US session;
- candidate level is frozen; it cannot drift after birth;
- each candidate cluster contributes at most one primary contact per structural episode.

## 7. Nearby neutral controls

The purpose is to test the **location**, not merely generic retracement behavior.

At candidate birth, create deterministic nearby pseudo-levels using the birth volatility `v_birth` at offsets:

`{-0.50v, -0.25v, +0.25v, +0.50v}` from the candidate center.

A pseudo-level is eligible only if:

- it lies strictly inside `(main_zhi, target_zlo)`;
- at birth it is below the current close and can therefore be approached from above;
- it is farther than `0.10 * v_birth` from every causal V3 candidate cluster already available in the episode;
- it is not inside MAIN or TARGET;
- it is frozen at candidate birth and never moved.

Controls use the same contact and reaction labeler. A primary matched candidate requires at least two contacted eligible controls. Candidate weight is one; its comparator is the mean outcome of its contacted controls.

Primary matched effect:

`mean(Y_candidate - mean(Y_contacted_neutral_controls))`.

Controls are local offsets rather than cross-session transplants so they preserve the same structural episode, trend, volatility regime, time of day, MAIN/TARGET geometry and retracement path as closely as possible.

## 8. Primary early-reaction outcome

The primary outcome measures immediate reaction and is independent of zone width.

At first contact:

- `v0` = causal volatility frozen at the contact state;
- anchor `A` = contact M1 close;
- contact-bar high/low are excluded from the outcome to avoid unknown intrabar ordering;
- favorable level = `A + 0.50 * v0`;
- adverse level = `A - 0.50 * v0`;
- horizon = next **10 available M1 bars**, truncated at 17:00 NY.

Classification:

- favorable first = 1;
- adverse first = 0;
- both in same M1 = 0 (`AMBIGUOUS_SAME_BAR`);
- neither within horizon = 0.

This is the confirmatory reaction-location endpoint.

### Fixed secondary reaction diagnostics

Reported without changing the primary decision:

- same symmetric first-passage outcome at `0.25v` within 5 M1;
- same at `0.50v` within 5 M1;
- same at `0.50v` within 15 M1;
- MFE/v and MAE/v over first 3, 5, 10 M1 after contact;
- time to +0.25v and +0.50v when reached;
- structural TARGET-vs-MAIN-close outcome as a secondary trade-context diagnostic only.

No secondary endpoint can rescue a failed primary result.

## 9. Low-latency execution modes

These are evaluated only from causal information available at the stated time. None changes candidate validity.

### `TOUCH_NEXT_OPEN`

- signal exists when contact bar closes;
- entry = next available M1 open;
- no candle-shape requirement.

### `CONTACT_RECLAIM_NEXT_OPEN`

- contact bar touched the level;
- contact bar close is strictly above candidate level;
- entry = next available M1 open;
- **no close-position threshold** and no bullish-color requirement.

### `CONTACT_BULL_RECLAIM_NEXT_OPEN`

- contact bar touched the level;
- `close > open` and `close > candidate level`;
- entry = next available M1 open;
- no wick-size rule and no 0.70 rule.

### `ONE_BAR_FIRST_BULL_RECLAIM`

- used only if contact bar did not qualify for `CONTACT_BULL_RECLAIM_NEXT_OPEN`;
- exactly one additional M1 bar may qualify with `close > open` and `close > candidate level`;
- entry = following M1 open;
- no waiting beyond that one additional bar.

For every mode record:

- minutes from contact to entry;
- `(entry - candidate_level) / v0`;
- whether +0.50v from the contact anchor had already been reached before entry;
- fraction of primary-success contacts whose +0.50v move was already completed before entry.

This directly measures the user's failure mode: confirmation arriving after the move has already left.

## 10. Candle geometry diagnostics

The following contact-candle descriptors are reported continuously, not converted into post-hoc thresholds:

- range / `v0`;
- body / range;
- close position in candle;
- close minus candidate level / `v0`;
- lower wick / range;
- lower wick / body where defined.

Prior research makes `range/v` and reclaim geometry particularly important diagnostics. Long lower wick is not assumed to be positive.

No threshold on these variables may be chosen after reading DEV or VAL and then called confirmatory in V3.

## 11. Historical windows and sealed holdout

- **DEV:** `2020-01-01 <= breakout < 2022-01-01`.
- **VAL:** `2022-01-01 <= breakout < 2023-01-01`.
- **REP:** `2023-01-01 <= breakout < 2024-01-01`.
- 2024–2026 may be used only for engineering/parity/runtime checks because substantial outcome research already exists there.

REP 2023 reaction outcomes remain sealed until the complete VAL continuation gate passes.

No refit, threshold change, candidate-family change, control-offset change, horizon change or trigger change is allowed after DEV outcomes are opened.

## 12. Statistical analysis

### Pooled candidate-cluster test — primary

For each period separately:

- candidate observations = contacted V3 candidate clusters with >=2 contacted local neutral controls;
- each candidate has weight one;
- primary effect = candidate binary outcome minus mean contacted-control outcome;
- inference = 5,000 fixed-seed bootstrap draws clustered by NY session and structural episode;
- report percentile 95% CI and one-sided p-value.

Mandatory quality gates:

- >=1,000 contacted candidate clusters in DEV and >=500 in VAL;
- >=120 NY sessions in DEV and >=80 in VAL;
- >=60% of contacted candidates retain >=2 contacted controls;
- matched-control balance absolute SMD <=0.10 for candidate/control relative corridor coordinate, contact minute, log volatility, trend15/v, trend60/v and trend240/v;
- no future/outcome field in candidate construction.

Pooled location PASS in VAL requires:

- all quality gates pass;
- point matched effect >0;
- bootstrap 95% lower bound >0.

### Candidate family diagnostics

`BROKEN_PIVOT_HIGH`, `POST_BREAK_PIVOT_LOW`, `BULL_FVG_MID`, and multi-family confluence are reported separately.

A family may be called individually `VALIDATED` only in REP, with:

- >=300 matched contacts;
- >=60 NY sessions;
- positive effect;
- Holm-adjusted one-sided p <0.05 across the three base families.

DEV/VAL family outputs are diagnostic and cannot be used to delete a weak family from the pooled REP definition.

## 13. Execution-usefulness gate

Location validity alone is not sufficient for a usable entry trigger.

In VAL, a trigger is eligible to continue only if:

- >=300 executions across >=60 sessions;
- its symmetric post-entry +0.50v/-0.50v 10-M1 first-passage rate is above 50% with session-bootstrap lower 95% bound >50%;
- median entry drift from candidate level <=0.25v;
- fewer than 20% of contacts that were primary location successes had already completed the +0.50v favorable move before the trigger entry.

`TOUCH_NEXT_OPEN` is the latency baseline. Confirmation modes must improve outcome quality without violating the latency gate. A delayed mode that looks better only because it enters after much of the move is excluded from production consideration.

## 14. Sequential decision tree

1. **PREOUTCOME engineering fail:** stop before DEV.
2. **DEV pooled location does not show positive effect or fails quality:** stop; no VAL outcomes.
3. **DEV passes:** freeze all code/definitions, then open VAL with no changes.
4. **VAL pooled location fails:** close V3; REP remains sealed.
5. **VAL pooled location passes but no low-latency execution mode passes:** location may remain a research finding; no entry trigger/Pine marker.
6. **VAL pooled location and at least one low-latency execution mode pass:** freeze everything and open REP 2023.
7. **REP confirms pooled location and at least one execution mode:** return to Pro for final Pine/production adjudication.

No result from a secondary diagnostic, candidate family, candle threshold, session slice or hand-picked example may rescue a failed primary gate.

## 15. Mandatory engineering gate before any full historical run

Because prior work lost substantial runtime to an avoidable implementation bottleneck, V3 must pass these checks before DEV outcomes:

- synthetic causal tests for candidate birth, arming, contact, MAIN invalidation and TARGET termination;
- legacy Z4 breakout/corridor episode parity against frozen structural engine on a known engineering interval;
- indexed M1/session access; no full-dataframe scan inside per-candidate loops;
- deterministic replay hash equality;
- one-month **outcome-blind candidate-generation runtime benchmark** completed before the full run;
- complete PREOUTCOME manifest/hash freeze;
- assertion that no V3 reaction label/report/model exists before outcome authorization.

The runtime benchmark may count candidates/controls and exercise contacts on known 2024–2026 engineering data, but it must not compute or report V3 post-contact reaction outcomes.

## 16. Production/Pine status

At preregistration:

`NO_PRODUCTION_AUTHORIZATION_V3_PREOUTCOME`

No candidate level, reaction marker, score, color or alert from V3 is authorized in Pine until the sequential DEV → VAL → conditional REP process and final Pro gate are complete.
