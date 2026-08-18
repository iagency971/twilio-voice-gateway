#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER = struct.Struct("<4sIIHHI36s")
RECORD = struct.Struct("<qffffIIII")
EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)


def sc_us(ts: datetime) -> int:
    return int((ts - EPOCH).total_seconds() * 1_000_000)


def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        scid = td / "GCZ26.scid"
        norm = td / "ticks.csv.gz"
        m1 = td / "m1.csv"
        with scid.open("wb") as f:
            f.write(HEADER.pack(b"SCID", 56, 40, 1, 0, 0, b"\0" * 36))
            rows = [
                (datetime(2026,8,17,12,0,0,tzinfo=timezone.utc), 4000.2,4000.0,4000.1,3,0,3),
                (datetime(2026,8,17,12,0,1,tzinfo=timezone.utc), 4000.1,3999.9,4000.0,2,2,0),
                (datetime(2026,8,17,12,1,0,tzinfo=timezone.utc), 4000.3,4000.1,4000.2,1,0,1),
            ]
            for ts, ask, bid, trade, size, bidv, askv in rows:
                f.write(RECORD.pack(sc_us(ts), 0.0, ask, bid, trade, 1, size, bidv, askv))

        subprocess.check_call([sys.executable, str(HERE/"ingest_sierra_scid.py"), str(scid), "--output", str(norm)])
        subprocess.check_call([sys.executable, str(HERE/"build_gc_m1_features.py"), str(norm), "--output", str(m1)])

        with gzip.open(norm, "rt", encoding="utf-8") as f:
            ticks = list(csv.DictReader(f))
        assert len(ticks) == 3
        assert [r["aggressor"] for r in ticks] == ["BUY", "SELL", "BUY"]
        assert ticks[0]["contract"] == "GCZ26"

        with m1.open("r", encoding="utf-8") as f:
            mins = list(csv.DictReader(f))
        assert len(mins) == 2
        assert float(mins[0]["volume"]) == 5.0
        assert float(mins[0]["bid_volume"]) == 2.0
        assert float(mins[0]["ask_volume"]) == 3.0
        assert float(mins[0]["delta"]) == 1.0
        assert int(mins[0]["trade_count"]) == 2
        assert abs(float(mins[0]["vwap"]) - ((4000.1*3 + 4000.0*2)/5)) < 1e-6
        print("GC_VENDOR_NEUTRAL_SMOKE_PASS")


if __name__ == "__main__":
    main()
