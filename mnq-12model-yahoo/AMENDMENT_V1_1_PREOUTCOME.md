# Amendment V1.1 — Yahoo source QA bridge (PRE-OUTCOME)

Status: `PREOUTCOME_QA_AMENDMENT`

This amendment is made **before any August economic trade ledger or P&L was successfully written**.

## Why V1 direct-parity QA was impossible
The actual Yahoo `NQ=F` 1-minute download began at 2026-07-28 00:09 ET. The independent true-MNQ ledger used by V1 ends on 2026-07-27. Therefore there are zero direct overlapping dates, making the originally preregistered Jul22-27 Yahoo-vs-true-MNQ check impossible by data availability rather than by price disagreement.

The first external strategy run then aborted while trying to save its CSV to a relative non-existent directory. It failed before `MetricsV2.print_report()` and before any August trade CSV or accepted economic result existed.

## Previously established bridge evidence
A separate source-parity audit, completed before this Yahoo test, compared the exact archived GetData snapshot against an independent true MNQ trade ledger over Jun1-Jul27:
- 39 overlap days.
- median absolute entry difference 0.25 NQ point.
- median absolute exit difference 0.25 point.
- 97.44% entries within 1 point.
- 92.31% exits within 1 point; 97.44% within 2 points.
- direction agreement 38/39 (97.44%).
- one known catastrophic mismatch on 2026-06-16.

No late-July mismatch was identified in that audit.

## V1.1 bridged Yahoo QA
Before any August P&L is interpreted, compare Yahoo `NQ=F` against the exact archived GetData snapshot over **Jul28-Jul31 RTH 09:30-15:59 ET**, minute by minute.

Required all:
1. >=4 overlap RTH dates.
2. >=1,200 overlapping one-minute bars.
3. median absolute close difference <=0.50 point.
4. >=95% closes within 1.00 point.
5. median of per-bar maximum OHLC absolute difference <=0.50 point.
6. >=95% of bars have maximum OHLC absolute difference <=2.00 points.

Interpretation: a QA PASS establishes a *bridged recent-price-parity screen* (true MNQ -> GetData through Jul27, and GetData -> Yahoo Jul28-31). It does NOT transform Yahoo into licensed CME validation.

## Economic protocol unchanged
The pinned May31 ensemble, August 3-20 evaluation dates, daily context, friction rescoring, and all economic gates in `PROTOCOL_V1.md` remain unchanged.

If bridged QA fails: no August economic interpretation.
If bridged QA passes: August result may be interpreted only as a forward sanity screen that can justify a longer licensed-CME validation.

No model/direction/date filter may be changed based on August outcomes.