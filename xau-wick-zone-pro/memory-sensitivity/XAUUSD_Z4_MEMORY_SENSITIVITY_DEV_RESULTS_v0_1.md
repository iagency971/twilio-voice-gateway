# XAUUSD Z4 — Memory Lookback DEV Sensitivity Results v0.1

**Status:** DEV COMPLETE — NO WINNER SELECTED — NO PRODUCTION CHANGE

Preregistered candidates: **240 / 360 / 600 / 900 / 1440 active M1**. The 1440 architecture remains the validated incumbent until a later decision gate.

| L | BID ΔBrier | BID weekly 95% | ASK ΔBrier | ASK weekly 95% | BID robust | Dual-feed strong | BID churn | Median lineage | Median zones/landmark |
|---:|---:|---:|---:|---:|:---:|:---:|---:|---:|---:|
| 240 | 0.00166826 | [-0.00020671, 0.00344817] | 0.00130471 | [-0.00026523, 0.00297281] | FAIL | FAIL | 0.209575 | 2.00 | 2.00 |
| 360 | 0.00089691 | [-0.00120625, 0.00310903] | 0.00121989 | [-0.00070224, 0.00356523] | FAIL | FAIL | 0.163794 | 3.00 | 3.00 |
| 600 | 0.00085351 | [-0.00063131, 0.00263262] | 0.00051670 | [-0.00119153, 0.00262320] | FAIL | FAIL | 0.116970 | 3.00 | 3.00 |
| 900 | 0.00156285 | [-0.00039165, 0.00434631] | 0.00060570 | [-0.00137475, 0.00346414] | FAIL | FAIL | 0.087733 | 3.00 | 4.00 |
| 1440 | 0.00147276 | [0.00069103, 0.00234559] | 0.00174284 | [0.00057578, 0.00344269] | PASS | PASS | 0.060491 | 3.00 | 6.00 |

## Fold-by-fold BID ΔBrier

| L | APR | MAY | JUN | JUL | Positive folds |
|---:|---:|---:|---:|---:|---:|
| 240 | 0.00337214 | -0.00075897 | 0.00183144 | 0.00230192 | 3/4 |
| 360 | 0.00505724 | -0.00163449 | -0.00317385 | 0.00298756 | 2/4 |
| 600 | -0.00088465 | 0.00055531 | 0.00161559 | 0.00220498 | 3/4 |
| 900 | -0.00415324 | 0.00239048 | 0.00380196 | 0.00436067 | 3/4 |
| 1440 | 0.00129697 | 0.00157570 | 0.00184918 | 0.00120617 | 4/4 |

## Frozen interpretation

- BID robust candidates: **[1440]**.
- Dual-feed strong candidates eligible for targeted Pro review: **[1440]**.
- This run does **not** choose the final memory.
- Raw Brier levels across memories are not used alone because each memory creates a different zone population/base rate.
- Geometry stability/churn is secondary and cannot rescue a candidate that loses predictive robustness.
- No Validation/OOS data was used in this gate.
- No Pine/R/production modification is authorized from this DEV sensitivity result alone.

## Next step

Run the planned **targeted Pro methodological gate** on this fixed five-candidate result set to decide whether the incumbent 1440 should remain frozen or whether a shorter memory deserves a separately frozen historical replication.
