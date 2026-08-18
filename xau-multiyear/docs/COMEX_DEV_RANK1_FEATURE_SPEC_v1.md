# XAUUSD Reaction Zones — COMEX DEV_RANK1 Feature Specification v1

Date: 2026-08-18
Status: frozen before DEV_RANK1 market-data acquisition.

## Scope

Phase-1 market information is restricted to:

- GC `ohlcv-1m` continuous context;
- GC `trades` on selected full research sessions;
- existing XAUUSD M1 price/event data.

No new TBBO, BBO-1m, BBO-1s, MBP-1 or MBO is part of this feature specification.

## Time and research-session convention

All event timestamps are UTC internally. New York local time uses `America/New_York` with timezone/DST handling.

The canonical research trading date is:

`research_trading_date(ts) = date(ts in America/New_York - 17 hours)`.

A **research session** is the set of GC records sharing this key. This definition is intentionally fixed across the historical sample rather than silently changing with historical exchange-hour conventions. It is not to be relabeled as an official exchange-session definition.

The existing wide acquisition envelope around a selected research date may contain records outside the research-session key; those records are retained raw but excluded from that session's profile.

Pilot maintenance-gap analysis is QA only and does not retrospectively alter the 17:00 New York research-date rule after outcomes are observed.

## Continuous-contract and roll rule

Request symbol: `GC.v.0` using Databento continuous symbology. Preserve returned `instrument_id` and free symbology mappings.

Any feature requiring price differences, cumulative signed flow or a profile resets when `instrument_id` changes.

No prior-session GC level is carried across a continuous-contract mapping change in the primary COMEX-native-zone study.

A local event spanning a mapping change is flagged `roll_crossing=1`; signed-flow/profile features for that event are excluded from the primary analysis.

## Price grid

GC standard Gold futures price grid for this research is one GC minimum tick, `$0.10/oz`. Every volume-at-price bin is an exact 0.10-price bin. Raw prices are rounded to the nearest tick only after verifying the record is within numerical tolerance of that grid.

If a mapped GC instrument is found whose valid price increment differs from $0.10, the feature engine must stop for that instrument and require a specification amendment before analysis.

## Data-quality flags

Preserve Databento `flags` and never discard them silently.

Primary handling:

- `F_LAST (128)`: retained, informational;
- `F_BAD_TS_RECV (8)`: `ts_recv` is not used as event time; retain record and set a QA flag;
- `F_MAYBE_BAD_BOOK (4)`: mark `data_gap_flag=1`. A local feature window containing this flag is excluded from primary local-flow analysis. Developing cumulative/profile features after the first such flag in a research session are invalid until the next research-session reset;
- `F_SNAPSHOT (32)`, `F_MBP (16)`, `F_TOB (64)` in the `trades` schema: report as unexpected-schema QA conditions; do not silently consume them;
- `F_PUBLISHER_SPECIFIC (2)`: preserve and report separately; no predictive interpretation without a dataset-specific frozen rule.

Sequence-number duplicates are not by themselves treated as duplicated trades. Raw-event identity follows the full DBN transaction payload / multiset QA used in the paid pilot.

## Side convention and uncertainty

Use native Databento side exactly as disseminated:

- `B`: buy aggressor;
- `A`: sell aggressor;
- `N`: no side specified.

No primary imputation of `N`.

For any window:

- `BVol = sum(size where side=B)`
- `AVol = sum(size where side=A)`
- `NVol = sum(size where side=N)`
- `TotalVol = BVol + AVol + NVol`
- `native_delta = BVol - AVol`
- `N_volume_share = NVol / TotalVol`
- `delta_lower_bound = native_delta - NVol`
- `delta_upper_bound = native_delta + NVol`
- `delta_sign_robust = +1` if `delta_lower_bound > 0`, `-1` if `delta_upper_bound < 0`, otherwise `0` (indeterminate).

CVD is stored as an interval, not a falsely precise scalar:

- `CVD_native(t) = cumulative(BVol - AVol)`
- `CVD_lower(t) = cumulative(BVol - AVol - NVol)`
- `CVD_upper(t) = cumulative(BVol - AVol + NVol)`

All CVD variants reset at the research-session boundary and at any instrument mapping change.

`N_volume_share` may be used only with explicit year / time-of-session / contract controls because `N` may reflect data-generation or auction mechanisms rather than pure order-flow alpha.

## M1 context features

All windows are backward-looking and end at the model's causal decision cutoff.

### Returns and volatility

For horizons `h ∈ {1,5,15,30}` minutes:

- `gc_ret_h_bps = 10000 * ln(close_t / close_{t-h})` when both closes exist within the same instrument mapping;
- `gc_range_h_bps = 10000 * (max(high)-min(low)) / close_t` over the last h active minutes.

Realized volatility:

- `gc_rv_15 = sqrt(sum(r_1m^2 over last 15 active minutes)) * 10000`
- `gc_rv_60 = sqrt(sum(r_1m^2 over last 60 active minutes)) * 10000`.

No value is bridged across a contract roll.

### Volume / relative volume

For `h ∈ {1,5,15,30}`:

- `gc_m1_volume_h = sum(ohlcv volume over the last h active minutes)`.

Relative volume baseline uses only prior research dates:

- find the same ending minute-of-research-session on each of the previous 20 research dates with valid GC M1 data;
- compute the corresponding h-minute volume sums;
- baseline is their median;
- `relvol_h = current_h_volume / max(previous20_median, 1 contract)`.

Require at least 10 valid prior research dates; otherwise relvol is missing. No future date contributes to the baseline.

### GC–XAU basis

At aligned M1 timestamps:

- `basis = GC_close - XAUUSD_close`;
- `basis_change_h = basis_t - basis_{t-h}` for h ∈ {1,5,15,30}.

Basis features are missing across GC mapping changes or stale/missing GC M1 bars. No back-adjusted continuous price is created.

## Local trade-flow features

Computed over backward windows ending at the decision cutoff for `h ∈ {1,5,15,30}` minutes:

- total traded volume;
- trade count;
- trade rate = count / elapsed active minutes;
- volume rate = volume / elapsed active minutes;
- mean trade size;
- median trade size;
- maximum trade size;
- AVol / BVol / NVol;
- A/B/N volume shares;
- native delta;
- normalized native delta = `(BVol-AVol)/TotalVol`;
- delta lower/upper bounds;
- robust delta sign;
- local VWAP;
- price change / TotalVol when TotalVol > 0;
- price change / abs(native_delta) when abs(native_delta) > 0, labeled a price-impact proxy, not direct absorption.

No arbitrary large-trade threshold is introduced in v1.

## Exact VWAP

For any causal record set with positive total size:

`VWAP = sum(price_i * size_i) / sum(size_i)`.

Two scopes are permitted:

1. local VWAP over the 1/5/15/30-minute causal windows;
2. research-session-to-date VWAP from the first GC trade in the current research-session key through the decision cutoff.

A completed prior research-session VWAP may be used in the next session.

## Volume-at-price profile

For a causal record set:

1. map each trade price to its 0.10 GC tick bin;
2. sum total volume by price bin, including A/B/N volume;
3. retain side-specific volume by bin as separate diagnostics.

### POC

POC is the bin with maximum total volume.

Tie break:

1. choose tied bin closest to the profile VWAP;
2. if still exactly tied, choose the lower price for deterministic reproducibility.

### Value Area (70%)

Start with POC. Repeatedly inspect the immediately adjacent unselected lower and upper tick bins:

- add the side with greater total volume;
- if equal, add both sides in the same expansion step;
- continue until cumulative selected volume is at least 70% of profile total volume.

`VAL` and `VAH` are the minimum and maximum selected tick prices.

No alternative 68%, 70%, 80% threshold is tested in DEV_RANK1.

### HVN / LVN — secondary fixed definitions

Use a centered three-tick moving-average of total volume across the causally available profile, with missing price bins inside the traded range filled with zero volume.

- HVN candidate: local maximum of smoothed volume and smoothed volume >= 75th percentile of positive-bin smoothed volumes;
- LVN candidate: local minimum between two traded bins and smoothed volume <= 25th percentile of positive-bin smoothed volumes;
- volume void: one or more consecutive zero-volume tick bins strictly between the profile minimum and maximum traded price.

No percentile or smoothing width is tuned inside DEV_RANK1. HVN/LVN/void results are secondary to VWAP/POC/VAH/VAL.

## Profile scopes

Permitted primary scopes:

- local 30-minute profile ending at decision cutoff;
- developing current research-session profile ending at decision cutoff;
- completed immediately previous research-session profile.

The final current-session profile is forbidden for decisions made before that session is complete.

## COMEX-native zone definitions

Primary static levels known after a completed prior research session:

- prior POC;
- prior VAH;
- prior VAL;
- prior terminal VWAP;
- prior fixed-definition HVNs/LVNs/void edges as secondary candidates.

A native-zone contact occurs when **GC itself**, not XAUUSD, first trades at the level's tick price after the level becomes known. This produces a timestamp. XAUUSD reaction/outcome is then measured from the synchronized XAUUSD state at that timestamp.

This avoids inventing a static conversion from a GC price level into an XAUUSD price level while the GC–XAU basis is changing.

For a prior-session level, only the first contact in the next research session is primary. Later contacts are secondary/repeated-contact diagnostics.

Current developing POC/VAH/VAL/VWAP are treated as time-varying features, not as hindsight-fixed static zones.

No prior-session level is carried across an instrument mapping change in the primary study.

## Causal decision cutoffs

Uniform stored local envelope for behavior comparison remains `contact -30m` through `contact +16m`, but predictors are truncated to:

- PASSIVE_TOUCH: strictly before contact-bar start;
- TOUCH_NEXT_OPEN: contact-bar close;
- ACCEPTANCE_RETEST: `t0 + 5m`;
- CLEAN_REJECTION: actual reclaim-bar close;
- FAILED_AUCTION: actual reclaim-bar close;
- RECLAIM_PULLBACK: actual reclaim-bar close;
- reclaim-based maximum: no later than `t0 + 16m`.

The 120-minute post-entry outcome horizon is never part of initial predictor construction.

## Missingness

Missing, rolled, invalidated or data-gap features remain missing and receive explicit missingness indicators in the model. They are not forward-filled across a session or contract boundary.

## Promotion rule

Only formulas in this document can enter the primary DEV_RANK1 feature groups. Any newly invented formula discovered after examining DEV_RANK1 outcomes is exploratory and cannot enter DEV_RANK2 unless it is separately documented as a protocol deviation and DEV_RANK2 is not used as confirmation for it.
