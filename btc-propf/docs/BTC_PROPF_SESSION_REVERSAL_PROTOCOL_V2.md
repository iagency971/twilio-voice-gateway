# BTC Prop-Firm Session Reversal Protocol V2

Status: PRE-VALIDATION / 2026 SEALED

Independent motivation: peer-reviewed cryptocurrency research documents both intraday momentum and reversal, with reversal related to overreaction and changing around large price jumps and liquidity conditions.

V2 keeps every V1 data, timing, stop, cost, candidate, selection and validation rule unchanged. The only architecture change is direction:
- if the first 30-minute session return is positive, the final 30-minute trade is SHORT;
- if the first 30-minute session return is negative, the final 30-minute trade is LONG.

Candidate set remains exactly six: B00/B08/B16 crossed with ALL/HIGHVOL. HIGHVOL remains range > shifted 20-session median. DEV = 2019-2023. Validation = 2024-2025. 2026 MUST NOT be downloaded or inspected. DEV and validation gates are identical to V1. No further rescue is permitted inside V2.
