#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import struct
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr

START = datetime(2026, 8, 16, tzinfo=timezone.utc)
END = datetime(2026, 8, 26, tzinfo=timezone.utc)
PRIMARY = "https://datafeed.dukascopy.com/datafeed"
FALLBACK = "https://www.dukascopy.com/datafeed"
FMT = ">IIIIIf"
REC = struct.calcsize(FMT)
PRICE_DIVISOR = 1000.0
CUTOFF = pd.Timestamp("2026-08-20 23:58:00Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_bytes(sess: requests.Session, url: str):
    last = None
    for attempt in range(1, 5):
        try:
            r = sess.get(url, timeout=(10, 45), allow_redirects=True)
            if r.status_code in (404, 410):
                return b"", r.status_code, r.url, attempt
            r.raise_for_status()
            return r.content, r.status_code, r.url, attempt
        except Exception as exc:
            last = exc
            time.sleep(2 * attempt)
    raise RuntimeError(f"download failed {url}: {last}")


def day_rows(sess: requests.Session, day: datetime, side: str, file_meta: list[dict]):
    rel = (
        f"XAUUSD/{day.year:04d}/{day.month - 1:02d}/{day.day:02d}/"
        f"{side.upper()}_candles_min_1.bi5"
    )
    used = raw = status = final = attempts = None
    errors = []
    for host in (PRIMARY, FALLBACK):
        try:
            raw, status, final, attempts = get_bytes(sess, host + "/" + rel)
            used = host
            break
        except Exception as exc:
            errors.append(f"{host}: {type(exc).__name__}: {exc}")
    if raw is None:
        raise RuntimeError(f"no transport succeeded for {rel}: {errors}")

    meta = {
        "day": day.date().isoformat(),
        "side": side,
        "relative_path": rel,
        "host": used,
        "status_code": status,
        "final_url": final,
        "attempts": attempts,
        "compressed_bytes": len(raw),
        "compressed_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
    }
    if not raw:
        meta.update({"records": 0, "decompressed_bytes": 0})
        file_meta.append(meta)
        return []

    decomp = lzma.LZMADecompressor(lzma.FORMAT_AUTO, None, None)
    try:
        dec = decomp.decompress(raw)
    except lzma.LZMAError as exc:
        raise RuntimeError(f"LZMA decode failed {rel}: {exc}") from exc
    if len(dec) % REC:
        raise RuntimeError(f"bad record length {rel}: {len(dec)} mod {REC}")

    rows = []
    for off in range(0, len(dec), REC):
        sec, o, h, l, c, volume = struct.unpack(FMT, dec[off : off + REC])
        ts = day + timedelta(seconds=int(sec))
        rows.append(
            (
                ts,
                o / PRICE_DIVISOR,
                h / PRICE_DIVISOR,
                l / PRICE_DIVISOR,
                c / PRICE_DIVISOR,
                float(volume),
            )
        )
    meta.update(
        {
            "records": len(rows),
            "decompressed_bytes": len(dec),
            "first_utc": str(rows[0][0]) if rows else None,
            "last_utc": str(rows[-1][0]) if rows else None,
        }
    )
    file_meta.append(meta)
    return rows


def acquire(outdir: Path):
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 XAU-raw-bi5-bridge-v0.4"
    file_meta: list[dict] = []
    direct = {}
    for side in ("bid", "ask"):
        rows = []
        day = START
        while day < END:
            rows.extend(day_rows(sess, day, side, file_meta))
            day += timedelta(days=1)
        df = (
            pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"])
            .sort_values("time")
            .drop_duplicates("time")
            .reset_index(drop=True)
        )
        if len(df) < 5000:
            raise RuntimeError(f"{side} insufficient decoded rows {len(df)}")
        df.to_csv(outdir / f"direct_{side}.csv", index=False)
        direct[side] = df
        print(side, len(df), df.time.min(), df.time.max(), flush=True)

    manifest = {
        "status": "RAW_BI5_DECODE_COMPLETE",
        "future_trade_outcomes_used": False,
        "format": FMT,
        "price_divisor": PRICE_DIVISOR,
        "window_utc": [START.isoformat(), END.isoformat()],
        "files": file_meta,
    }
    (outdir / "file_manifest.json").write_text(json.dumps(manifest, indent=2))
    return direct


def apply_bridge(direct: dict[str, pd.DataFrame], archive: Path, forex: Path, outdir: Path):
    old = pd.read_csv(archive)
    old["time"] = pd.to_datetime(old.timestamp, utc=True)
    old = old.sort_values("time").drop_duplicates("time")

    bridge = {}
    all_pass = True
    for side, d in direct.items():
        cols = ["open", "high", "low", "close"]
        oldcols = [c + "_" + side for c in cols]
        m = old[["time"] + oldcols].merge(d[["time"] + cols], on="time", how="left")
        coverage = float(m["close"].notna().mean())
        common = m.dropna(subset=cols).copy()
        checks = {
            "timestamp_coverage_ge_0995": coverage >= 0.995,
            "common_rows_ge_5000": len(common) >= 5000,
        }
        a = pd.to_numeric(common["close_" + side], errors="raise").to_numpy(float)
        b = pd.to_numeric(common["close"], errors="raise").to_numpy(float)
        rs = float(spearmanr(np.diff(np.log(a)), np.diff(np.log(b))).statistic) if len(common) > 3 else None
        checks["return_spearman_ge_0999"] = rs is not None and rs >= 0.999
        errs = {}
        for c in cols:
            x = pd.to_numeric(common[c + "_" + side], errors="raise").to_numpy(float)
            y = pd.to_numeric(common[c], errors="raise").to_numpy(float)
            e = np.abs(x - y)
            errs[c] = {
                "median": float(np.median(e)),
                "p99": float(np.quantile(e, 0.99)),
                "max": float(np.max(e)),
            }
            checks[f"{c}_median_le_0001"] = errs[c]["median"] <= 0.001
            checks[f"{c}_p99_le_001"] = errs[c]["p99"] <= 0.01
            checks[f"{c}_max_le_005"] = errs[c]["max"] <= 0.05
        passed = all(checks.values())
        all_pass = all_pass and passed
        bridge[side] = {
            "pass": passed,
            "direct_rows": int(len(d)),
            "direct_min_utc": str(d.time.min()),
            "direct_max_utc": str(d.time.max()),
            "archive_rows": int(len(old)),
            "coverage": coverage,
            "common_rows": int(len(common)),
            "return_spearman": rs,
            "errors_usd": errs,
            "checks": checks,
        }

    result = {
        "status": "DUKASCOPY_RAW_BI5_BRIDGE_PASS" if all_pass else "DUKASCOPY_RAW_BI5_BRIDGE_FAIL",
        "future_trade_outcomes_used": False,
        "decoder": {"format": FMT, "price_divisor": PRICE_DIVISOR},
        "bridge": bridge,
    }
    (outdir / "bridge_result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)

    ext = {"bridge_pass": all_pass}
    if all_pass:
        bid = direct["bid"][["time", "open", "high", "low", "close"]].rename(
            columns={c: c + "_bid" for c in ["open", "high", "low", "close"]}
        )
        ask = direct["ask"][["time", "open", "high", "low", "close"]].rename(
            columns={c: c + "_ask" for c in ["open", "high", "low", "close"]}
        )
        merged = bid.merge(ask, on="time", how="inner", validate="one_to_one")
        for c in ["open", "high", "low", "close"]:
            merged[c] = (merged[c + "_bid"] + merged[c + "_ask"]) / 2.0
        merged["spread"] = merged.close_ask - merged.close_bid
        merged["timestamp"] = merged.time.dt.strftime("%Y-%m-%d %H:%M:%S%z")

        f = pd.read_csv(forex)
        f["time"] = pd.to_datetime(f.timestamp_utc, utc=True)
        lo, hi = f.time.min(), f.time.max()
        inter = merged[(merged.time >= lo) & (merged.time <= hi)].copy()
        extra = int((inter.time > CUTOFF).sum())
        keep = [
            "timestamp", "open", "high", "low", "close",
            "open_bid", "high_bid", "low_bid", "close_bid",
            "open_ask", "high_ask", "low_ask", "close_ask", "spread",
        ]
        inter[keep].to_csv(outdir / "direct_merged_intersection.csv", index=False)
        ext.update(
            {
                "status": "DIRECT_EXTENSION_READY" if extra >= 500 else "DIRECT_EXTENSION_INSUFFICIENT",
                "intersection_rows": int(len(inter)),
                "intersection_min_utc": str(inter.time.min()),
                "intersection_max_utc": str(inter.time.max()),
                "post_2026_08_20_2358_rows": extra,
                "meets_extra_500": extra >= 500,
                "merged_sha256": sha256(outdir / "direct_merged_intersection.csv"),
            }
        )
    (outdir / "extension_meta.json").write_text(json.dumps(ext, indent=2))
    print(json.dumps(ext, indent=2), flush=True)
    return all_pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--forex", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    direct = acquire(outdir)
    apply_bridge(direct, Path(args.archive), Path(args.forex), outdir)


if __name__ == "__main__":
    main()
