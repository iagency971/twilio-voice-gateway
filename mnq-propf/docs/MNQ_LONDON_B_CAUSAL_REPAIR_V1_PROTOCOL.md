# MNQ London B — Causal Repair V1

Status before outcomes: `PRE_2025_PROTOCOL_FROZEN`

## Goal
Test whether the published/replicated **London Session Signal B** survives a strictly causal implementation suitable for later prop-firm evaluation.

## Signal specification retained from the public replication
- Asset: MNQ quarterly futures.
- Source bars: 1-minute `Last` OHLCV, resampled to 15-minute bars.
- London session: 03:00–08:30 America/New_York.
- Features on London 15-minute bars only:
  1. 5-bar return;
  2. bar range / 20-bar mean range;
  3. 20-bar volume z-score;
  4. 5-bar realized volatility;
  5. intrabar location `(close-low)/(high-low)`.
- StandardScaler + GaussianMixture, 3 full-covariance components, random_state 42, n_init 5, max_iter 200.
- Regime identity: low/medium/high volatility = 0/1/2.
- Signal: clean `0 -> 2` transition with no regime 1 in the previous two bars.
- Direction: LONG only.
- Entry: next 15-minute bar open, same London session/day only.
- Exit: close of the fourth 15-minute bar after entry (60 elapsed minutes) or the 08:15 bar close, whichever occurs first.
- Primary friction: 2.0 MNQ index points round trip.
- Stress friction: 4.0 points round trip.

## Causal repairs versus the public approximate code
1. **No full-sample GMM.** For test year Y, scaler/GMM are fit only on years < Y.
2. **No test-set regime remapping.** Raw GMM components are mapped to 0/1/2 using realized-volatility means on the training sample only; that mapping is frozen for Y.
3. **No cross-session entry.** A signal near 08:30 cannot enter the next day.
4. **Exact 60-minute hold.** Four 15-minute bars inclusive of the entry bar; no off-by-one fifth bar.
5. **Causal futures roll.** The active contract can only roll forward. A roll decision for day D uses the most recent prior RTH (09:30–16:00 ET) volume for which both current and next contracts have data. If next volume exceeds current volume, next becomes active from D. No future-day volume is used.
6. **Feature reset at each contract roll** so contract gaps cannot enter 5/20-bar features.

## Data boundary
External public source: `mbytes21/MNQ_DATA`, quarterly MNQ contract directories. Only dates <= 2024-12-31 may be read in this stage. 2025 and 2026 outcomes are forbidden.

## Sequential pre-2025 tests
- 2022: train on all available 2019–2021 data.
- 2023: train on all available 2019–2022 data.
- 2024: train on all available 2019–2023 data.

No parameters are selected from these years: there is one frozen rule.

## Gate to authorize opening 2025
All must hold on combined 2022–2024 causal test trades:
- N >= 60;
- mean net >= +2.0 points/trade at 2-point friction;
- t-stat >= 2.0;
- profit factor >= 1.30;
- each of 2022, 2023, 2024 has positive net mean;
- at 4-point friction, mean net > 0 and PF > 1.10.

If any gate fails: terminal status `MNQ_LONDON_B_CAUSAL_REPAIR_V1_PRE2025_NO_GO`; do not read or calculate 2025/2026 performance.

If all gates pass: `MNQ_LONDON_B_CAUSAL_REPAIR_V1_AUTHORIZE_2025_REPLICATION`; freeze implementation and only then open 2025. 2026 remains reserved for a later independent/cross-source confirmation.
