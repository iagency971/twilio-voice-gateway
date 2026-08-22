# US100 Zero-Paid-Data — VWAP Rejection V2 Conclusion

Final status: `VWAP_REJECTION_V2_DEV_NO_GO`

The family used only native M1 OHLC, tick volume and recorded MT spread and therefore satisfied the zero-paid-data operational constraint. However, none of the nine predeclared VWAP/ATR rejection variants passed the 2021–2023 DEV gates.

The least-negative/highest-expectancy end of the grid was K=2.0 / RR=2.0:
- PRIMARY N=741, expectancy +0.04295R/trade, total +31.83R, PF=1.0659, max DD=36R;
- 2021 expectancy -0.09129R, 2022 +0.07570R, 2023 +0.13988R;
- STRESS expectancy +0.01866R, PF=1.0283, max DD=46R.

It failed expectancy, PF, max-DD, all-years-positive and stress-PF gates. `selected=null`.

No V2 2024 outcome was opened. No rescue tuning is permitted.