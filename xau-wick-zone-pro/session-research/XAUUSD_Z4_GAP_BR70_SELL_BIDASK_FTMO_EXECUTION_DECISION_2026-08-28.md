# XAUUSD standalone Z4-gap BR70 SELL — BID/ASK + FTMO execution decision

Date: 2026-08-28
Branch: `agent/xau-wick-zone-pro-dev`
Status: **EXECUTION VALIDATION FAIL — NO CONFIRMATION CANDIDATE / NO PRODUCTION**

## 1. Scope

This memo closes the preregistered execution study:

`XAUUSD_Z4_GAP_BR70_SELL_DUKASCOPY_BIDASK_FTMO_COMMISSION_PREREG_v1_0_2026-08-28.md`

Prereg blob: `499fb629647c2d2ed793c981435de61c31761bef`.

The signal ledger was not changed. Source trades are the immutable standalone Z4-gap BR70 SELL trades produced by workflow run `33203080123`:

- no E1/E2/E3 requirement;
- no prerequisite Z4 break;
- bearish BR70 while price is strictly in the open gap between two adjacent causal Z4s;
- entry next M1 open;
- target = upper boundary of the lower Z4;
- structural invalidation trigger = confirmed M1 BID close above the lower boundary of the upper Z4;
- same session only.

This execution layer changes only how an already-frozen SELL can actually enter/exit when BID and ASK are distinguished.

## 2. Data integrity

Dukascopy source family: `kevingtlin/Market-Data-Lab`, pinned commit:

`3fbaf3280338474b379e3a01ac3396f85d4a60be`

Period: Aug 2024 through Jul 2026, 24 BID + 24 ASK monthly M1 files.

QA:

- all 24 BID files pass the already-frozen project SHA-256 manifest;
- all 24 ASK files are present at the pinned source commit and pass the source audit (`ok` or documented `ok_market_session` for recent market-session-only files);
- BID rows = 1,037,578;
- ASK rows = 1,037,578;
- active exact-timestamp inner join rows = 1,037,578;
- source frozen trades = 10,235;
- executable trades reconstructed = 10,235;
- maximum absolute BID entry-price parity error versus the frozen ledger = **0.0**.

Therefore the execution failure below is not caused by lost trade rows, timestamp drift, or changed BID input.

Primary workflow run: `33204504441`.
Final artifact:
- ID `9699120292`;
- name `z4-gap-br70-sell-bidask-ftmo-v1`;
- digest `sha256:b3c9102d0b361913f0d7eb7f163bf05edbe58100706e561189ad2e7d773902b0`.

## 3. Frozen executable SELL convention

- entry = BID open at the already-frozen next-M1 entry time;
- TP is executable only when ASK low reaches the frozen lower-Z4 target;
- TP fill = frozen target price;
- invalidation trigger remains BID close above the frozen upper-Z4 structural boundary;
- invalidation fill = ASK close of that M1;
- if executable TP and BID-close invalidation coexist on one M1, invalidation is taken first (conservative);
- unresolved trades are liquidated at ASK close at session end;
- risk denominator = `stop_zlo - entry_bid_open`;
- current FTMO Metals CFD commission modeled at `0.0007%` of notional per side (`0.000007` decimal per side);
- no extra synthetic spread is subtracted because Dukascopy BID/ASK already contains source spread.

Important: Dukascopy historical spread is **not claimed to be FTMO historical spread**. FTMO commission is applied separately.

## 4. Observed Dukascopy spread

Across the 10,235 frozen entry times:

- mean entry spread: **$0.649/oz**;
- median: **$0.597/oz**;
- p90: **$0.870/oz**;
- p95: **$1.027/oz**;
- p99: **$1.993/oz**.

Exit close spread context:

- mean: **$0.659/oz**;
- median: **$0.597/oz**;
- p90: **$0.877/oz**;
- p95: **$1.090/oz**;
- p99: **$2.257/oz**.

Initial Z4-to-Z4 risk is much larger in absolute dollars (median about $4.95/oz over the full ledger), but the strategy's raw expectancy was small enough that spread still dominates the edge.

## 5. Exact BID/ASK execution results

### One position at a time — gross BID/ASK before FTMO commission

| Session | H1 gross R | H2 gross R |
|---|---:|---:|
| US 08–17 | -0.217 | -0.195 |
| Asia 18–03 | -0.273 | -0.189 |
| Asia Core 21–03 | -0.279 | -0.073 |
| Europe 03–08 | -0.359 | -0.117 |

All eight session x half cells are negative **before commission**.

### One position at a time — after current FTMO commission

| Session | H1 net R | H2 net R |
|---|---:|---:|
| US 08–17 | **-0.233** | **-0.207** |
| Asia 18–03 | **-0.292** | **-0.201** |
| Asia Core 21–03 | **-0.297** | **-0.085** |
| Europe 03–08 | **-0.377** | **-0.129** |

Pooled descriptive one-position result:

- H1: **-0.290R**, PF_R **0.590**, N=3,550;
- H2: **-0.165R**, PF_R **0.735**, N=3,532.

Current FTMO commission itself adds an average penalty of only about:

- H1 one-position: ~0.0178R/trade;
- H2 one-position: ~0.0117R/trade.

Therefore **commission is not the primary reason the setup fails**. The failure already exists in gross BID/ASK execution.

Extra adverse slippage only worsens the result.

## 6. Why the BID-only result disappeared

Previous BID-only session-liquidation robustness, one position at a time, was:

- H1: +0.050R;
- H2: +0.064R.

Exact BID/ASK materially changes that for three reasons.

### A. Target executability

The BID-only study had 5,124 `TP_FIRST` trades.

Under exact ASK-side cover requirements:

- 4,742 remain executable TP (**92.54%**);
- 293 eventually invalidate before ASK reaches the target;
- 89 remain unresolved and are liquidated at session end.

Retention of original BID-only TPs:

- US H1 91.0%, H2 94.8%;
- Asia Broad H1 90.3%, H2 94.7%;
- Asia Core H1 91.3%, H2 95.1%;
- Europe H1 88.0%, H2 94.9%.

So a seemingly small 5–12% loss of BID-only TPs is highly damaging to a low-edge strategy.

### B. Confirmed-close invalidations overshoot the nominal -1R boundary

The earlier structural ledger deliberately counted an invalidation as `-1R` at the frozen Z4 boundary.

With an executable confirmed-close rule, original invalidations exit after the M1 has actually closed beyond that boundary. Even using the BID close hypothetically, the original invalidation set averages roughly **-1.247R**, not -1R.

The ASK close then adds another spread penalty; the same original invalidation set averages roughly **-1.504R** gross executable.

Thus approximately half an R of additional average loss appears on invalidations relative to the structural abstraction:

- ~0.247R from close-through / overshoot on BID;
- ~0.257R from ASK-side exit spread on those invalidations.

This is a structural execution issue, not commission.

### C. Session liquidation pays the ASK spread

Original `NEITHER` trades had approximately +0.124R average BID-close liquidation in the prior diagnostic. With ASK-side liquidation their gross average becomes approximately -0.023R.

## 7. FTMO spread cross-check

Dukascopy median spread near $0.60/oz is not assumed to equal FTMO.

However, an independent public dataset captured from `FTMO-Server4` reports XAUUSD:

- `point = 0.01`;
- live spread field = floating;
- an 8-trading-day May 2026 spread sample with XAUUSD hourly p50 values roughly **41–53 points = $0.41–$0.53/oz** for most quoted hours;
- its README summarizes a calm median XAUUSD spread around **$0.45/oz**.

A separate March 2026 independent FTMO review reported about **$0.27** Gold spread during a London-session observation.

These are third-party observations, not an official historical FTMO tick archive. They show that Dukascopy's $0.60 median is somewhat wider, but not obviously orders of magnitude wider than observed FTMO XAUUSD conditions.

Official FTMO information states that spreads are live/variable. Its Sep 2025 commission update introduced Metals CFD commission of **0.0007% of volume per side**, which is the commission used here.

## 8. Scientific decision

The preregistered gate is a clear **FAIL**:

- pooled one-position expectancy after exact BID/ASK + current FTMO commission is negative in H1 and H2;
- zero of four sessions are positive in both halves;
- `confirmation_candidate = false`.

Therefore:

1. **Do not promote the standalone Z4-gap BR70 SELL.**
2. **Do not restore E1/E2/E3 as a mandatory filter**: the matched control already showed no incremental E benefit.
3. Do not tune session/hour/RR/BR threshold on H1/H2 to rescue the setup after seeing this execution result.
4. The earlier positive BID-only expectation must be treated as a structural-price phenomenon that is insufficiently large under realistic two-sided Gold CFD execution.
5. A genuine future test would require either:
   - a materially different preregistered entry/execution architecture whose expected edge is large enough relative to spread; or
   - exact historical/forward FTMO BID/ASK execution data demonstrating much tighter effective spreads at the actual signal timestamps.

Current production authorization: **NONE**.

## 9. What remains valid from the research

The research still establishes useful facts:

- bearish rejection in a Z4 gap has a small BID-only directional tendency toward the lower Z4;
- E1/E2/E3 are not necessary to explain that tendency;
- the tendency is too small versus observed Gold CFD execution costs under the current standalone mechanics;
- confirmed-close invalidation is materially more expensive in live-fill terms than a nominal `-1R` boundary assumption.

The correct next design work should focus on **execution-aware entry/invalidation mechanics**, not on retrospectively selecting the prettiest E rank or session.
