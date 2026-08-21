# CL EIA / Non-EIA — Free 2026 Proxy Screen V1

Status before proxy outcomes: `PREOUTCOME_FROZEN_PROXY_SCREEN`.
This screen does NOT replace `PROTOCOL_V1.md` and cannot produce a validation PASS.

## Source
Public GetData Finance `USOIL_1m.csv` sample, UTC bars, approximately 2026-02-01 through 2026-07-31. It is a WTI/USOIL proxy rather than official CME CL; therefore all outcomes are `PROXY_ONLY`.

## Frozen rules
Exactly the CL translation already frozen in `PROTOCOL_V1.md`:
- non-EIA: 09:00 open -> 09:29 close determines direction; trade 14:00 open -> 14:29 close;
- standard Wednesday EIA: 10:30 open -> 10:59 close determines direction; trade 14:00 open -> 14:29 close;
- official holiday-shift EIA release sessions are excluded entirely from V1.

For the available 2026 sample the official EIA holiday-shift sessions excluded are:
- 2026-02-19 (Thursday, 12:00 ET);
- 2026-05-28 (Thursday, 12:00 ET).
Their preceding Wednesdays are ordinary non-EIA days under the frozen classification.
All other Wednesdays in the sample with the standard 10:30 ET WPSR are EIA days.

PRIMARY friction = 0.03 WTI points per trade.
STRESS friction = 0.05 WTI points per trade.
No stop, TP, threshold, volatility filter, direction filter, weekday filter, or post-result rescue.

## Proxy screening gates
### Non-EIA engine
All required to justify official-CME download for this engine:
1. >= 80 trades.
2. PRIMARY mean net points > 0.
3. PRIMARY PF >= 1.05.
4. STRESS mean net points > 0.
5. Remove best 5%: remaining PRIMARY mean >= 0.

### EIA engine
All required to justify official-CME download for this engine:
6. >= 18 standard EIA trades.
7. PRIMARY mean net points > 0.
8. PRIMARY PF >= 1.15.
9. STRESS mean net points > 0.
10. Remove best 10%: remaining PRIMARY mean >= 0.

Terminal proxy states:
- both engines pass: `PROXY_BOTH_PASS_JUSTIFY_CME`;
- only EIA passes: `PROXY_EIA_PASS_JUSTIFY_CME`;
- only non-EIA passes: `PROXY_NON_EIA_PASS_JUSTIFY_CME`;
- neither passes: `PROXY_NO_GO_DO_NOT_BUY_CME_DATA`.

No rules may be changed based on proxy outcomes before the official-CME test.
