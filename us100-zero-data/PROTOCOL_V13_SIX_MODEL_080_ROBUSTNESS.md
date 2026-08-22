# V13 — Six-Model 0.80% FTMO Robustness Stress

Status: `FROZEN_BEFORE_V13_RESULTS`

## Frozen candidate from V12

Models only:
- ema_rev
- kalman_mom
- open_drive
- ou_rev
- pd_rev
- pm_mom

Fixed risk: **0.80% of initial account per trade**.

No model, direction, threshold, exit, or sizing parameter may change in V13.

## Input

Use the frozen V5.3 native-US100 rescored ledger and the free complete-session calendar already used in V9/V10.

No paid data.

## Simulation

Block-bootstrap complete trading sessions while preserving all trades and their intraday order inside each sampled session.

- block lengths: 5, 10, 20 consecutive sessions;
- 25,000 simulations per scenario;
- maximum 250 sessions per FTMO step;
- Step 1 target +10%;
- Step 2 target +5%;
- minimum 4 active trading days per step;
- daily loss breach at −5%;
- total loss breach at −10%.

Run both PRIMARY and STRESS P&L streams.

## Floating-equity probes

Run two fixed adverse probes before every historical trade close:

- `−1.00R` probe;
- `−1.25R` probe.

The −1.25R probe is the decisive conservative scenario. It is not a claim about true MAE; it is an operational stress proxy because tick-level trade MAE is unavailable.

## Decisive robustness gate

Use **20-session blocks + STRESS + −1.25R floating probe**.

Require all:
- Step 1 pass probability >= 80%;
- combined two-step pass probability >= 70%;
- median Step 1 <= 55 sessions;
- median combined two-step <= 90 sessions;
- Step-1 daily-loss failure share <= 10%;
- Step-1 total-loss failure share <= 15%.

PASS means only `ROBUST_ENOUGH_FOR_FTMO_FREE_TRIAL`, never funded/live-ready.

## Limitation

Historical bootstrap cannot guarantee future regimes or exact FTMO price/spread/fill parity. A prospective FTMO Free Trial on native US100.cash remains mandatory after PASS.
