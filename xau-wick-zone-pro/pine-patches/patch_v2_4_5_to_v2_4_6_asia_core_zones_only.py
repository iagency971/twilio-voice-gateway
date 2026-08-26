#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

SOURCE_SHA256 = "85764a6d76ae8ce1ba6f4d89e71362b36bc8514d66084913e9b3ba9878ac4e44"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def replace_once(src: str, old: str, new: str, label: str) -> str:
    n = src.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly 1 occurrence, found {n}")
    return src.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="canonical XAUUSD_Z4_EBUY_QA_v2_4_5...pine")
    ap.add_argument("output", help="output v2.4.6 .pine")
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    raw = inp.read_bytes()
    got = sha256_bytes(raw)
    if got != SOURCE_SHA256:
        raise RuntimeError(f"source SHA mismatch: got {got}, expected {SOURCE_SHA256}")
    s = raw.decode("utf-8")

    s = replace_once(
        s,
        '"XAUUSD Z4 + E-BUY QA v2.4.5 - M1 BUY ZONE MEMORY / MTF ZONES"',
        '"XAUUSD Z4 + E-BUY QA v2.4.6 - ASIA CORE ZONES / US SIGNALS"',
        "indicator title",
    )

    s = replace_once(
        s,
        'bool showUSSession = input.bool(false, "Ombrer US 08:00–17:00 New York")',
        'bool showUSSession = input.bool(false, "Ombrer US 08:00–17:00 New York")\n'
        'bool showAsiaCoreSession = input.bool(false, "Ombrer Asia Core 21:00–03:00 New York")',
        "session shading input",
    )

    s = replace_once(
        s,
        'bool showEntryZones = input.bool(true, "Afficher zones d’entrée E-BUY (M1)")',
        'bool showEntryZones = input.bool(true, "Afficher zones d’entrée E-BUY (M1)")\n'
        'bool showAsiaCoreZones = input.bool(true, "Afficher zones E-BUY Asia Core 21:00–03:00 NY", tooltip = "Zones uniquement. BULL_REJECTION, E_BUY_US, BUY et alertes restent strictement US 08:00–17:00 NY.")',
        "Asia Core zone input",
    )

    s = replace_once(
        s,
        'bool inUS = not na(time(timeframe.period, "0800-1700", "America/New_York"))\n'
        'bgcolor(showUSSession and inUS ? color.new(color.blue, 94) : na)',
        'bool inUS = not na(time(timeframe.period, "0800-1700", "America/New_York"))\n'
        'bool inAsiaCoreClock = not na(time(timeframe.period, "2100-0300", "America/New_York"))\n'
        'bool inAsiaCore = showAsiaCoreZones and inAsiaCoreClock\n'
        'bool inEntryZoneSession = inUS or inAsiaCore\n'
        'bgcolor(showUSSession and inUS ? color.new(color.blue, 94) : showAsiaCoreSession and inAsiaCoreClock ? color.new(color.teal, 94) : na)',
        "session flags",
    )

    s = replace_once(
        s,
        'bool eligibleEntry = inUS and upperCount > 0 and targetIdx >= 0',
        'bool eligibleEntry = inEntryZoneSession and upperCount > 0 and targetIdx >= 0',
        "E-BUY display eligibility",
    )

    s = replace_once(
        s,
        'if eEntryActive and not na(eEntrySnapshotTime) and time > eEntrySnapshotTime and time < eEntrySnapshotTime + LANDMARK_MS\n'
        '        qi := 0',
        'if inUS and eEntryActive and not na(eEntrySnapshotTime) and time > eEntrySnapshotTime and time < eEntrySnapshotTime + LANDMARK_MS\n'
        '        qi := 0',
        "confirmed contact scan US-only",
    )

    s = replace_once(
        s,
        'if time < endT and open < target',
        'if inUS and time < endT and open < target',
        "next-open E score / BUY US-only",
    )

    s = replace_once(
        s,
        'float eBRLiveV = na\n'
        'if isM1 and showBRState and barstate.islast',
        'float eBRLiveV = na\n'
        '// Asia Core is zones-only: remove any stale US BR label outside the US session.\n'
        'if isM1 and not inUS and barstate.islast and not na(eBRStateLabel)\n'
        '    label.delete(eBRStateLabel)\n'
        '    eBRStateLabel := na\n'
        'if isM1 and inUS and showBRState and barstate.islast',
        "live BR US-only",
    )

    s = replace_once(
        s,
        'string eTxt = "E" + str.tostring(ei + 1) + " · E" + (na(eZoneScore) ? "—" : str.tostring(eZoneScore))',
        'string eTxt = "E" + str.tostring(ei + 1) + (inAsiaCore ? " · ASIA" : " · E" + (na(eZoneScore) ? "—" : str.tostring(eZoneScore)))',
        "Asia zone label",
    )

    s = replace_once(
        s,
        'if isM1 and not barstate.ishistory and showEntrySignals and eBuySignalBar',
        'if isM1 and inUS and not barstate.ishistory and showEntrySignals and eBuySignalBar',
        "realtime BUY redraw US-only",
    )

    s = replace_once(
        s,
        'plotshape(showEntrySignals and eBuySignalBar, title = "E-BUY validated"',
        'plotshape(showEntrySignals and inUS and eBuySignalBar, title = "E-BUY validated"',
        "BUY plot US-only",
    )

    s = replace_once(
        s,
        'bool eBuyAlertPulse = isM1 and barstate.isnew and eBuySignalBar',
        'bool eBuyAlertPulse = isM1 and inUS and barstate.isnew and eBuySignalBar',
        "BUY alert US-only",
    )

    s = replace_once(
        s,
        'table.cell(eDebugTable, 1, 0, isM1 ? "M1 VALIDATED" : "M1 ONLY")',
        'table.cell(eDebugTable, 1, 0, isM1 ? (inUS ? "US · ZONES+BR+E+BUY" : inAsiaCore ? "ASIA CORE · ZONES ONLY" : "M1 · HORS E-BUY") : "M1 ONLY")',
        "debug session status",
    )

    s = replace_once(
        s,
        'table.cell(eDebugTable, 1, 1, "E >= " + str.tostring(entryMinE))',
        'table.cell(eDebugTable, 1, 1, inUS ? "E >= " + str.tostring(entryMinE) : inAsiaCore ? "N/A · ZONES ONLY" : "—")',
        "debug filter status",
    )

    status_anchor = '// v2.4.5 UX: v2.4.4 + exact matched E-zone memory drawn over BUY bar + next 2 bars; realtime-safe persistent BUY state retained.'
    status_new = status_anchor + '\n// v2.4.6: scientific E-BUY zones also displayed during Asia Core 21:00–03:00 NY after fresh Aug-2026 location PASS.\n// Asia Core remains ZONES ONLY: BR, E_BUY_US, BUY, BUY-zone-memory and BUY alerts are US-only after reaction gate FAIL (H1 27.37%, H2 27.15%, Aug 21.96% TP1 resolved).'
    s = replace_once(s, status_anchor, status_new, "scientific status")

    # Static safety assertions on the patched source.
    required = [
        'bool inAsiaCoreClock = not na(time(timeframe.period, "2100-0300", "America/New_York"))',
        'bool eligibleEntry = inEntryZoneSession and upperCount > 0 and targetIdx >= 0',
        'if inUS and eEntryActive and not na(eEntrySnapshotTime)',
        'if inUS and time < endT and open < target',
        'if isM1 and inUS and showBRState and barstate.islast',
        'plotshape(showEntrySignals and inUS and eBuySignalBar',
        'bool eBuyAlertPulse = isM1 and inUS and barstate.isnew and eBuySignalBar',
        'ASIA CORE · ZONES ONLY',
    ]
    for x in required:
        if x not in s:
            raise RuntimeError(f"patched safety assertion missing: {x}")

    forbidden = [
        'bool eligibleEntry = inUS and upperCount > 0 and targetIdx >= 0',
        'if isM1 and showBRState and barstate.islast',
        'plotshape(showEntrySignals and eBuySignalBar, title = "E-BUY validated"',
        'bool eBuyAlertPulse = isM1 and barstate.isnew and eBuySignalBar',
    ]
    for x in forbidden:
        if x in s:
            raise RuntimeError(f"unsafe legacy anchor remains: {x}")

    out.write_text(s, encoding="utf-8")
    print(f"SOURCE_SHA256={got}")
    print(f"OUTPUT_SHA256={sha256_bytes(out.read_bytes())}")
    print(f"OUTPUT={out}")


if __name__ == "__main__":
    main()
