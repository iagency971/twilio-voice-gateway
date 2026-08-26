# XAUUSD Z4 + E-BUY Pine v2.4.6 — Asia Core zones-only QA

## Canonical source

Patch applies only to:
- `XAUUSD_Z4_EBUY_QA_v2_4_5_M1_ENTRY_BUY_ZONE_MEMORY_QA_PROXY.pine`
- SHA-256 `85764a6d76ae8ce1ba6f4d89e71362b36bc8514d66084913e9b3ba9878ac4e44`

Patcher:
- `xau-wick-zone-pro/pine-patches/patch_v2_4_5_to_v2_4_6_asia_core_zones_only.py`

## Scientific authorization encoded

### US 08:00–17:00 America/New_York
Unchanged scientific behavior:
- E-BUY zones;
- causal contact / BULL_REJECTION;
- frozen `E_BUY_US` rank;
- BUY threshold / next-M1-open signal;
- BUY memory;
- alerts.

### Asia Core 21:00–03:00 America/New_York
Authorized:
- E-BUY zones only using the same fixed C5 architecture and sticky top-3.

Not authorized and therefore hard-disabled:
- BULL_REJECTION state/markers;
- `E_BUY_US` computation/zone score;
- BUY signals;
- BUY memory;
- BUY alerts.

Evidence basis:
- fresh Aug-2026 location holdout PASS: coverage 1v 83.60%, 1.5v 93.46%, 2v 97.53%, survival-aware persistence 97.81%;
- Asia-Core BR reaction FAIL: H1 TP1 resolved 27.37%, H2 27.15%, fresh Aug 21.96%, all below preregistered 30% transfer floor.

## Deterministic code changes

1. Add `inAsiaCoreClock = 21:00–03:00 NY` and optional Asia-Core zone/shading inputs.
2. E-BUY display eligibility becomes `inUS OR enabled Asia Core`.
3. Confirmed contact scan remains `inUS` only.
4. Next-open E-score/BUY calculation remains `inUS` only.
5. Real-time BR UX remains `inUS` only and stale label is removed outside US.
6. BUY plot/realtime redraw/alert are defensively gated `inUS`.
7. Asia zone label renders `E1 · ASIA`, `E2 · ASIA`, `E3 · ASIA` rather than an E score.
8. Debug status explicitly reports `ASIA CORE · ZONES ONLY`.

## TradingView QA checklist

On M1 FOREXCOM:XAUUSD:

- 20:55 NY: no E-BUY Asia-Core display.
- 21:00 NY: Asia-Core E-BUY zones may initialize if normal target/zone eligibility exists.
- 21:00–02:59 NY: labels must be `E1 · ASIA`, etc.; no BR x/✓; no BUY; no E score; no BUY alert.
- 23:55 → 00:00 NY: sticky-zone continuity is allowed (5-minute continuity across midnight).
- 03:00 NY: Asia-Core E-BUY display must clear; 03:00–07:59 is outside the E-BUY session layer.
- 08:00 NY: US E-BUY behavior resumes with the existing E score / BR / BUY logic.
- 17:00 NY: US E-BUY signal layer stops as before.

US regression check:
- replay a known US interval already inspected under v2.4.5;
- US E-zone geometry/slots must be unchanged;
- historical BUY markers and E values must be unchanged;
- no new alert can fire outside US.

## Important implementation note

The patcher verifies the exact v2.4.5 SHA before modifying anything. If the source differs by even one byte, it aborts rather than silently patching a non-canonical file.
