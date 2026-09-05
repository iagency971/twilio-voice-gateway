# VWAP Rejection V2.2 — Ambiguous Signal Bar Amendment

Status: `PRE_V2_DEV_ECONOMICS_FROZEN`

Written before any V2 economic outcome is calculated. If the same closed M1 bar simultaneously satisfies both the LONG and SHORT VWAP/ATR rejection conditions, that bar is treated as ambiguous and produces no signal. Scanning continues to the next bar within the predeclared signal window.

No other V2 rule changes.