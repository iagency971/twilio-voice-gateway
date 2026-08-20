#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bisect
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

START_DATE = pd.Timestamp("2019-05-01")
END_DATE = pd.Timestamp("2024-12-31")
TEST_YEARS = [2022, 2023, 2024]
PRIMARY_FRICTION = 2.0
STRESS_FRICTION = 4.0

CONTRACT_RE = re.compile(r"MNQ\s+(\d{2})-(\d{2})$")


def contract_key(name: str):
    m = CONTRACT_RE.search(name)
    if not m:
        return None
    month = int(m.group(1))
    year = 2000 + int(m.group(2))
    return year, month


def file_date(path: Path):
    try:
        return pd.Timestamp(path.name[:8])
    except Exception:
        return None


def hhmm_minutes(ts: pd.Series) -> pd.Series:
    return ts.dt.hour * 60 + ts.dt.minute


def discover_contracts(root: Path):
    dirs = []
    for p in root.glob("MNQ *"):
        if p.is_dir() and contract_key(p.name):
            dirs.append(p)
    return sorted(dirs, key=lambda p: contract_key(p.name))


def pass1_volume_and_files(contract_dirs, out: Path):
    volume = {}
    files = {}
    coverage = []
    for cdir in contract_dirs:
        cname = cdir.name
        volume[cname] = {}
        files[cname] = {}
        n_ok = 0
        min_d = None
        max_d = None
        for fp in sorted(cdir.glob("*.Last.csv")):
            d = file_date(fp)
            if d is None or d < START_DATE or d > END_DATE:
                continue
            try:
                x = pd.read_csv(fp, usecols=["datetime", "volume"])
                x["datetime"] = pd.to_datetime(x["datetime"], errors="coerce")
                x["volume"] = pd.to_numeric(x["volume"], errors="coerce").fillna(0.0)
                x = x.dropna(subset=["datetime"])
                mins = hhmm_minutes(x["datetime"])
                # Prior-day RTH volume is fully known before next day's London session.
                rth = x[(mins >= 570) & (mins < 960)]
                v = float(rth["volume"].sum())
                volume[cname][d] = v
                files[cname][d] = fp
                n_ok += 1
                min_d = d if min_d is None else min(min_d, d)
                max_d = d if max_d is None else max(max_d, d)
            except Exception as e:
                coverage.append({"contract": cname, "file": fp.name, "status": f"parse_error:{e}"})
        coverage.append({
            "contract": cname,
            "file": "*",
            "status": "ok",
            "n_dates": n_ok,
            "min_date": str(min_d.date()) if min_d is not None else None,
            "max_date": str(max_d.date()) if max_d is not None else None,
        })
    pd.DataFrame(coverage).to_csv(out / "source_coverage.csv", index=False)
    return volume, files


def build_roll_schedule(contract_dirs, volume, files, out: Path):
    names = [p.name for p in contract_dirs]
    union_dates = sorted({d for c in names for d in files.get(c, {}) if START_DATE <= d <= END_DATE})
    if not union_dates:
        raise RuntimeError("no source dates")

    joint = {}
    for i in range(len(names) - 1):
        a, b = names[i], names[i + 1]
        joint[(a, b)] = sorted(set(volume[a]).intersection(volume[b]))

    first_d = union_dates[0]
    idx = next((i for i, c in enumerate(names) if first_d in files[c]), None)
    if idx is None:
        raise RuntimeError("cannot initialize active contract")

    selected = {}
    rolls = []
    for d in union_dates:
        if d.weekday() >= 5:
            continue
        # Roll only forward, using the most recent PRIOR RTH date shared by current and next.
        changed = True
        while changed and idx < len(names) - 1:
            changed = False
            cur, nxt = names[idx], names[idx + 1]
            jd = joint[(cur, nxt)]
            k = bisect.bisect_left(jd, d) - 1
            if k >= 0:
                pv = jd[k]
                cv = float(volume[cur].get(pv, 0.0))
                nv = float(volume[nxt].get(pv, 0.0))
                if nv > cv and nv > 0:
                    rolls.append({"effective_date": str(d.date()), "from": cur, "to": nxt,
                                  "decision_date": str(pv.date()), "current_rth_volume": cv,
                                  "next_rth_volume": nv, "reason": "prior_rth_volume_cross"})
                    idx += 1
                    changed = True
                    continue
            # If current has disappeared, a forced forward roll is allowed only to a contract with data today.
            if d not in files[cur] and d in files[nxt]:
                rolls.append({"effective_date": str(d.date()), "from": cur, "to": nxt,
                              "decision_date": None, "current_rth_volume": None,
                              "next_rth_volume": None, "reason": "current_contract_missing"})
                idx += 1
                changed = True
        cur = names[idx]
        if d in files[cur]:
            selected[d] = cur

    pd.DataFrame(rolls).to_csv(out / "roll_schedule.csv", index=False)
    return selected, rolls


def load_selected_london_15m(selected, files, out: Path):
    rows = []
    day_qc = []
    prev_contract = None
    segment = -1
    for d, cname in sorted(selected.items()):
        if cname != prev_contract:
            segment += 1
            prev_contract = cname
        fp = files[cname][d]
        try:
            x = pd.read_csv(fp, usecols=["datetime", "open", "high", "low", "close", "volume"])
            x["datetime"] = pd.to_datetime(x["datetime"], errors="coerce")
            for c in ["open", "high", "low", "close", "volume"]:
                x[c] = pd.to_numeric(x[c], errors="coerce")
            x = x.dropna(subset=["datetime", "open", "high", "low", "close"])
            mins = hhmm_minutes(x["datetime"])
            x = x[(mins >= 180) & (mins < 510)].copy()  # 03:00 <= ET < 08:30
            if x.empty:
                day_qc.append({"date": str(d.date()), "contract": cname, "status": "no_london_rows"})
                continue
            x = x.set_index("datetime").sort_index()
            b = x.resample("15min", label="left", closed="left").agg(
                open=("open", "first"), high=("high", "max"), low=("low", "min"),
                close=("close", "last"), volume=("volume", "sum"))
            b = b.dropna(subset=["open", "high", "low", "close"])
            bm = b.index.hour * 60 + b.index.minute
            b = b[(bm >= 180) & (bm < 510)]
            if len(b) < 18:
                day_qc.append({"date": str(d.date()), "contract": cname, "status": "partial_london",
                               "bars": int(len(b))})
                continue
            day_qc.append({"date": str(d.date()), "contract": cname, "status": "ok",
                           "bars": int(len(b)), "segment": segment})
            for ts, r in b.iterrows():
                rows.append({"dt": ts, "date": d.normalize(), "contract": cname, "segment": segment,
                             "open": float(r.open), "high": float(r.high), "low": float(r.low),
                             "close": float(r.close), "volume": float(r.volume)})
        except Exception as e:
            day_qc.append({"date": str(d.date()), "contract": cname, "status": f"parse_error:{e}"})
    pd.DataFrame(day_qc).to_csv(out / "london_day_qc.csv", index=False)
    bars = pd.DataFrame(rows).sort_values("dt").reset_index(drop=True)
    if bars.empty:
        raise RuntimeError("no London 15m bars")
    bars.to_csv(out / "london_15m_selected.csv", index=False)
    return bars, day_qc


def build_features(bars: pd.DataFrame):
    parts = []
    for seg, g in bars.groupby("segment", sort=True):
        g = g.sort_values("dt").copy()
        f = pd.DataFrame(index=g.index)
        f["ret_5"] = g["close"].pct_change(5)
        rng = g["high"] - g["low"]
        mean_rng = rng.rolling(20, min_periods=20).mean()
        f["norm_range"] = rng / mean_rng.replace(0, np.nan)
        vm = g["volume"].rolling(20, min_periods=20).mean()
        vs = g["volume"].rolling(20, min_periods=20).std()
        f["vol_zscore"] = (g["volume"] - vm) / vs.replace(0, np.nan)
        lr = np.log(g["close"] / g["close"].shift(1))
        f["realized_vol"] = lr.rolling(5, min_periods=5).std()
        hl = (g["high"] - g["low"]).replace(0, np.nan)
        f["intrabar_loc"] = ((g["close"] - g["low"]) / hl).clip(0, 1)
        for c in ["dt", "date", "contract", "segment"]:
            f[c] = g[c]
        f = f.dropna(subset=["ret_5", "norm_range", "vol_zscore", "realized_vol", "intrabar_loc"])
        parts.append(f)
    return pd.concat(parts).sort_values("dt") if parts else pd.DataFrame()


def fit_predict_causal(features: pd.DataFrame, test_year: int):
    cols = ["ret_5", "norm_range", "vol_zscore", "realized_vol", "intrabar_loc"]
    train = features[features["dt"].dt.year < test_year].copy()
    test = features[features["dt"].dt.year == test_year].copy()
    if len(train) < 500 or test.empty:
        raise RuntimeError(f"insufficient features for {test_year}: train={len(train)} test={len(test)}")
    scaler = StandardScaler()
    Xtr = scaler.fit_transform(train[cols].to_numpy())
    gmm = GaussianMixture(n_components=3, covariance_type="full", random_state=42,
                          n_init=5, max_iter=200)
    raw_tr = gmm.fit_predict(Xtr)
    tr_map_df = pd.DataFrame({"raw": raw_tr, "rv": train["realized_vol"].to_numpy()})
    order = tr_map_df.groupby("raw")["rv"].mean().sort_values().index.tolist()
    if len(order) != 3:
        raise RuntimeError(f"GMM mapping incomplete for {test_year}")
    label_map = {int(raw): int(new) for new, raw in enumerate(order)}
    mapped_tr = pd.Series([label_map[int(x)] for x in raw_tr], index=train.index)
    raw_te = gmm.predict(scaler.transform(test[cols].to_numpy()))
    mapped_te = pd.Series([label_map[int(x)] for x in raw_te], index=test.index)
    return train, test, mapped_tr, mapped_te, label_map


def signals_for_year(features, test_year):
    train, test, rtr, rte, label_map = fit_predict_causal(features, test_year)
    # Only last train observations are needed as causal context at the year boundary, but all are safe.
    ctx = pd.concat([
        train[["dt", "date", "contract", "segment"]].assign(regime=rtr),
        test[["dt", "date", "contract", "segment"]].assign(regime=rte),
    ]).sort_values("dt")
    sig = []
    vals = ctx.reset_index(drop=True)
    for i in range(2, len(vals)):
        r = vals.iloc[i]
        if int(pd.Timestamp(r.dt).year) != test_year:
            continue
        p1, p2 = vals.iloc[i - 1], vals.iloc[i - 2]
        if not (r.segment == p1.segment == p2.segment):
            continue
        if int(p1.regime) == 0 and int(r.regime) == 2 and int(p1.regime) != 1 and int(p2.regime) != 1:
            sig.append({"signal_time": pd.Timestamp(r.dt), "date": pd.Timestamp(r.date),
                        "contract": r.contract, "segment": int(r.segment), "test_year": test_year})
    return pd.DataFrame(sig), label_map, len(train), len(test)


def simulate_signals(bars: pd.DataFrame, signals: pd.DataFrame, friction: float):
    trades = []
    if signals.empty:
        return pd.DataFrame()
    by_day = {(pd.Timestamp(d), int(s)): g.sort_values("dt").reset_index(drop=True)
              for (d, s), g in bars.groupby(["date", "segment"])}
    for _, s in signals.iterrows():
        key = (pd.Timestamp(s.date), int(s.segment))
        g = by_day.get(key)
        if g is None or g.empty:
            continue
        pos = g.index[g.dt.eq(pd.Timestamp(s.signal_time))].tolist()
        if len(pos) != 1:
            continue
        i = pos[0]
        entry_i = i + 1
        if entry_i >= len(g):
            continue
        entry_bar = g.iloc[entry_i]
        if pd.Timestamp(entry_bar.dt).date() != pd.Timestamp(s.signal_time).date():
            continue
        entry_min = pd.Timestamp(entry_bar.dt).hour * 60 + pd.Timestamp(entry_bar.dt).minute
        if entry_min >= 510:
            continue
        # Four 15m bars including the entry bar: exit on close of entry_i+3.
        desired = entry_i + 3
        allowed = g.index[(g.dt.dt.hour * 60 + g.dt.dt.minute) <= 495].tolist()  # <= 08:15 bar
        if not allowed:
            continue
        exit_i = min(desired, max(allowed))
        if exit_i < entry_i:
            continue
        exit_bar = g.iloc[exit_i]
        entry = float(entry_bar.open)
        exit_px = float(exit_bar.close)
        gross = exit_px - entry
        net = gross - friction
        trades.append({"test_year": int(s.test_year), "signal_time": str(s.signal_time),
                       "entry_time": str(entry_bar.dt), "exit_time": str(exit_bar.dt),
                       "contract": s.contract, "entry": entry, "exit": exit_px,
                       "gross_points": gross, "friction_points": friction, "net_points": net})
    return pd.DataFrame(trades)


def metrics(x: pd.DataFrame):
    if x.empty:
        return {"n": 0, "mean": None, "sum": 0.0, "t_stat": None, "win_rate": None,
                "pf": None, "max_dd_points": None}
    r = x.net_points.astype(float).to_numpy()
    n = len(r)
    sd = float(np.std(r, ddof=1)) if n > 1 else float("nan")
    t = float(np.mean(r) / (sd / math.sqrt(n))) if n > 1 and sd > 0 else None
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 0 else (float("inf") if pos > 0 else None)
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peak - eq, 0)
    return {"n": int(n), "mean": float(np.mean(r)), "sum": float(np.sum(r)), "t_stat": t,
            "win_rate": float(np.mean(r > 0)), "pf": pf,
            "max_dd_points": float(dd.max(initial=0.0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--out", default="mnq-propf/results/london_b_causal_v1")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(args.source_root)

    try:
        contracts = discover_contracts(source)
        if not contracts:
            raise RuntimeError(f"no contracts in {source}")
        volume, files = pass1_volume_and_files(contracts, out)
        selected, rolls = build_roll_schedule(contracts, volume, files, out)
        bars, day_qc = load_selected_london_15m(selected, files, out)
        bars["dt"] = pd.to_datetime(bars["dt"])
        bars["date"] = pd.to_datetime(bars["date"])
        feats = build_features(bars)
        if feats.empty:
            raise RuntimeError("no features")
        feats["dt"] = pd.to_datetime(feats["dt"])
        feats["date"] = pd.to_datetime(feats["date"])

        primary_all = []
        stress_all = []
        fold_meta = []
        annual = []
        for y in TEST_YEARS:
            sig, label_map, ntr, nte = signals_for_year(feats, y)
            p = simulate_signals(bars, sig, PRIMARY_FRICTION)
            s = simulate_signals(bars, sig, STRESS_FRICTION)
            if not p.empty:
                primary_all.append(p)
            if not s.empty:
                stress_all.append(s)
            pm, sm = metrics(p), metrics(s)
            annual.append({"year": y, "scenario": "PRIMARY", **pm})
            annual.append({"year": y, "scenario": "STRESS", **sm})
            fold_meta.append({"test_year": y, "train_feature_rows": ntr, "test_feature_rows": nte,
                              "signals": int(len(sig)), "label_map": json.dumps(label_map, sort_keys=True)})

        P = pd.concat(primary_all, ignore_index=True) if primary_all else pd.DataFrame(columns=["net_points"])
        S = pd.concat(stress_all, ignore_index=True) if stress_all else pd.DataFrame(columns=["net_points"])
        P.to_csv(out / "trades_primary.csv", index=False)
        S.to_csv(out / "trades_stress.csv", index=False)
        pd.DataFrame(annual).to_csv(out / "annual_metrics.csv", index=False)
        pd.DataFrame(fold_meta).to_csv(out / "fold_metadata.csv", index=False)

        pm = metrics(P)
        sm = metrics(S)
        annual_primary = {str(r["year"]): r for r in annual if r["scenario"] == "PRIMARY"}
        gates = {
            "combined_n_ge_60": pm["n"] >= 60,
            "combined_mean_ge_2pt": pm["mean"] is not None and pm["mean"] >= 2.0,
            "combined_t_ge_2": pm["t_stat"] is not None and pm["t_stat"] >= 2.0,
            "combined_pf_ge_1_30": pm["pf"] is not None and pm["pf"] >= 1.30,
            "year_2022_positive": annual_primary.get("2022", {}).get("mean") is not None and annual_primary["2022"]["mean"] > 0,
            "year_2023_positive": annual_primary.get("2023", {}).get("mean") is not None and annual_primary["2023"]["mean"] > 0,
            "year_2024_positive": annual_primary.get("2024", {}).get("mean") is not None and annual_primary["2024"]["mean"] > 0,
            "stress_mean_positive": sm["mean"] is not None and sm["mean"] > 0,
            "stress_pf_gt_1_10": sm["pf"] is not None and sm["pf"] > 1.10,
        }
        passed = all(gates.values())
        status = ("MNQ_LONDON_B_CAUSAL_REPAIR_V1_AUTHORIZE_2025_REPLICATION" if passed
                  else "MNQ_LONDON_B_CAUSAL_REPAIR_V1_PRE2025_NO_GO")
        result = {
            "status": status,
            "data_boundary": {"start": str(START_DATE.date()), "end": str(END_DATE.date()),
                              "2025_opened": False, "2026_opened": False},
            "contracts_discovered": [p.name for p in contracts],
            "selected_dates": int(len(selected)), "roll_count": int(len(rolls)),
            "london_15m_bars": int(len(bars)), "feature_rows": int(len(feats)),
            "primary": pm, "stress": sm, "annual": annual, "gates": gates,
            "notes": [
                "Public GMM feature set retained, but GMM/scaler fit causally on prior years only.",
                "Regime label mapping learned on training realized-volatility means only.",
                "No cross-session entry; exact four-bar/60-minute hold; feature reset on roll.",
                "2025/2026 are not read or calculated in this stage."
            ]
        }
        (out / "RESULT.json").write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2, allow_nan=False))
    except Exception as e:
        result = {"status": "MNQ_LONDON_B_CAUSAL_REPAIR_V1_INVALID_ABORT", "error": repr(e),
                  "2025_opened": False, "2026_opened": False}
        (out / "RESULT.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        raise


if __name__ == "__main__":
    main()
