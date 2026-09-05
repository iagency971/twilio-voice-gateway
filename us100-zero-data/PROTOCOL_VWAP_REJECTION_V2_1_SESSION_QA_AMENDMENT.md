# VWAP Rejection V2.1 — Candidate Session QA Amendment

Status: `PRE_V2_DEV_ECONOMICS_FROZEN`

Written before any V2 strategy outcome is calculated. Strategy rules and gates in `PROTOCOL_VWAP_REJECTION_V2.md` are unchanged.

For V2 frequency denominators and eligibility, a broker day is a `candidate session` only if:
- all 30 one-minute bars from 16:30 through 16:59 are present contiguously; and
- at least 120 M1 bars are present in the signal window 17:00 through 20:29.

No missing minute is forward-filled. This is data/session QA only.