#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

TZ_NY = "America/New_York"
SNAPSHOT_STEP = pd.Timedelta(minutes=5)
MATCH_TOL_V = 0.25
EPS = 1e-12

REQUIRED_INPUT = (
    "time", "v60", "entry_rank", "family", "center", "zlo", "zhi"
)
CONTEXT_INPUT_ALLOWED_BUT_DROPPED = {
    "close", "upper_z4_count", "nearest_upper_z4_dist_v", "distance_v"
}
FORBIDDEN_PATTERNS = (
    "mfe", "mae", "tp", "sl", "profit", "pnl", "expect", "payoff", "winrate",
    "success", "reaction", "favorable_first", "adverse_first", "invalidation",
    "w5", "w15", "w30", "w60", "future", "outcome", "return_", "r_multiple"
)

OUTPUT_COLUMNS = (
    "episode_id",
    "episode_seq",
    "snapshot_time_utc",
    "session_date_ny",
    "display_slot_rank",
    "current_family",
    "origin_family",
    "center",
    "zlo",
    "zhi",
    "v_snapshot",
    "zone_width_v",
    "episode_age_c5",
    "is_new_episode",
    "prior_snapshot_time_utc",
    "prior_display_slot_rank",
    "family_changed",
    "center_shift_v",
    "zlo_shift_v",
    "zhi_shift_v",
    "row_sha256",
)

MODEL_FEATURE_WHITELIST = (
    "zone_width_v",
    "episode_age_c5",
    "current_family",
    "origin_family",
)


@dataclass
class State:
    episode_seq: int
    episode_id: str
    age: int
    slot: int
    family: str
    origin_family: str
    center: float
    zlo: float
    zhi: float
    v: float
    time: pd.Timestamp


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Outcome-blind E intrinsic snapshot ledger V1")
    p.add_argument("--candidates", required=True, help="Frozen v0.4 sticky candidate CSV/CSV.GZ")
    p.add_argument("--output", required=True, help="Deterministic CSV.GZ output")
    p.add_argument("--manifest", required=True, help="JSON manifest output")
    p.add_argument("--expected-source-sha256", default=None)
    return p.parse_args()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _forbidden_input_columns(columns: Iterable[str]) -> list[str]:
    bad = []
    exact_tokens = {"mfe","mae","tp","tp1","tp2","sl","profit","pnl","expectancy","payoff","winrate","success","reaction","outcome","future","invalidation"}
    for c in columns:
        lc = str(c).lower()
        toks = [t for t in lc.replace("-","_").split("_") if t]
        token_bad = any(t in exact_tokens or t.startswith("mfe") or t.startswith("mae") or t.startswith("tp") and t[2:].isdigit() for t in toks)
        phrase_bad = any(pat in lc for pat in ("favorable_first","adverse_first","r_multiple","return_"))
        window_bad = any(t in {"w5","w15","w30","w60"} for t in toks)
        if token_bad or phrase_bad or window_bad:
            bad.append(str(c))
    return sorted(bad)


def read_candidates(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    missing = [c for c in REQUIRED_INPUT if c not in d.columns]
    if missing:
        raise ValueError(f"missing required candidate columns: {missing}")
    bad = _forbidden_input_columns(d.columns)
    if bad:
        raise ValueError(f"future/outcome-like columns forbidden in candidate input: {bad}")

    d = d.loc[:, list(dict.fromkeys(list(REQUIRED_INPUT) + [c for c in CONTEXT_INPUT_ALLOWED_BUT_DROPPED if c in d.columns]))].copy()
    d["time"] = pd.to_datetime(d["time"], utc=True)
    for c in ["v60", "center", "zlo", "zhi"]:
        d[c] = pd.to_numeric(d[c], errors="raise").astype(float)
    d["entry_rank"] = pd.to_numeric(d["entry_rank"], errors="raise").astype(int)
    d["family"] = d["family"].astype(str)

    ny = d["time"].dt.tz_convert(TZ_NY)
    m = (ny.dt.hour >= 8) & (ny.dt.hour < 17)
    d = d[m].copy()
    if d.empty:
        raise ValueError("no US 08:00-17:00 New York candidate snapshots")

    d = d.sort_values(["time", "entry_rank", "center", "family"], kind="mergesort").reset_index(drop=True)
    return d


def overlap(a_lo: float, a_hi: float, b_lo: float, b_hi: float) -> bool:
    return min(a_hi, b_hi) + EPS >= max(a_lo, b_lo)


def states_match(prev: State, row: pd.Series, cur_v: float) -> bool:
    tol = MATCH_TOL_V * max(prev.v, cur_v)
    return overlap(prev.zlo, prev.zhi, float(row.zlo), float(row.zhi)) or abs(prev.center - float(row.center)) <= tol + EPS


def _canonical_value(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, (np.floating, float)):
        return format(float(v), ".10g")
    if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
        return str(int(v))
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return str(v) if not isinstance(v, (str, bool)) else v

def deterministic_row_hash(values: dict) -> str:
    canonical = {str(k): _canonical_value(v) for k, v in values.items()}
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assign_episodes(candidates: pd.DataFrame) -> pd.DataFrame:
    out: list[dict] = []
    next_seq = 1
    prev_states: list[State] = []
    prev_time: pd.Timestamp | None = None

    for t, g in candidates.groupby("time", sort=True):
        t = pd.Timestamp(t)
        g = g.sort_values(["entry_rank", "center", "family"], kind="mergesort")
        if g["entry_rank"].duplicated().any():
            raise ValueError(f"duplicate display slot at {t}")
        if len(g) > 3:
            raise ValueError(f"more than 3 displayed zones at {t}: {len(g)}")
        if not np.all(np.isfinite(g["v60"])) or (g["v60"] <= 0).any():
            raise ValueError(f"invalid v60 at {t}")

        contiguous = prev_time is not None and (t - prev_time == SNAPSHOT_STEP)
        used_prev: set[int] = set()
        current_states: list[State] = []

        for _, r in g.iterrows():
            slot = int(r.entry_rank)
            cur_v = float(r.v60)
            center, zlo, zhi = float(r.center), float(r.zlo), float(r.zhi)
            if not (np.isfinite(center) and np.isfinite(zlo) and np.isfinite(zhi) and zlo <= center <= zhi):
                raise ValueError(f"invalid zone geometry at {t} slot {slot}")
            family = str(r.family)

            candidates_prev = []
            if contiguous:
                for j, p in enumerate(prev_states):
                    if j in used_prev:
                        continue
                    if states_match(p, r, cur_v):
                        candidates_prev.append((abs(p.center - center), p.episode_seq, j, p))

            if candidates_prev:
                _, _, j, p = min(candidates_prev, key=lambda x: (x[0], x[1], x[2]))
                used_prev.add(j)
                seq = p.episode_seq
                eid = p.episode_id
                age = p.age + 1
                origin = p.origin_family
                is_new = 0
                prior_time = p.time
                prior_slot = p.slot
                family_changed = int(family != p.family)
                center_shift_v = (center - p.center) / cur_v
                zlo_shift_v = (zlo - p.zlo) / cur_v
                zhi_shift_v = (zhi - p.zhi) / cur_v
            else:
                seq = next_seq
                eid = f"EIV1-{seq:08d}"
                next_seq += 1
                age = 1
                origin = family
                is_new = 1
                prior_time = pd.NaT
                prior_slot = np.nan
                family_changed = 0
                center_shift_v = np.nan
                zlo_shift_v = np.nan
                zhi_shift_v = np.nan

            ny = t.tz_convert(TZ_NY)
            rec = {
                "episode_id": eid,
                "episode_seq": int(seq),
                "snapshot_time_utc": t.isoformat(),
                "session_date_ny": ny.date().isoformat(),
                "display_slot_rank": slot,
                "current_family": family,
                "origin_family": origin,
                "center": center,
                "zlo": zlo,
                "zhi": zhi,
                "v_snapshot": cur_v,
                "zone_width_v": (zhi - zlo) / cur_v,
                "episode_age_c5": int(age),
                "is_new_episode": int(is_new),
                "prior_snapshot_time_utc": None if pd.isna(prior_time) else pd.Timestamp(prior_time).isoformat(),
                "prior_display_slot_rank": None if pd.isna(prior_slot) else int(prior_slot),
                "family_changed": int(family_changed),
                "center_shift_v": None if not np.isfinite(center_shift_v) else float(center_shift_v),
                "zlo_shift_v": None if not np.isfinite(zlo_shift_v) else float(zlo_shift_v),
                "zhi_shift_v": None if not np.isfinite(zhi_shift_v) else float(zhi_shift_v),
            }
            rec["row_sha256"] = deterministic_row_hash(rec)
            out.append(rec)
            current_states.append(State(seq, eid, age, slot, family, origin, center, zlo, zhi, cur_v, t))

        prev_states = current_states
        prev_time = t

    result = pd.DataFrame(out, columns=OUTPUT_COLUMNS)
    if result.empty:
        raise ValueError("empty intrinsic ledger")
    return result


def dataframe_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n", float_format="%.10g")
    return buf.getvalue().encode("utf-8")


def write_deterministic_gzip(df: pd.DataFrame, path: Path) -> None:
    raw = dataframe_csv_bytes(df)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fout:
        with gzip.GzipFile(filename="", mode="wb", fileobj=fout, mtime=0, compresslevel=9) as gz:
            gz.write(raw)


def build_manifest(source_path: Path, output_path: Path, ledger: pd.DataFrame, expected_source_sha256: str | None) -> dict:
    source_sha = sha256_file(source_path)
    if expected_source_sha256 and source_sha != expected_source_sha256:
        raise ValueError(f"candidate source SHA256 mismatch: got {source_sha}, expected {expected_source_sha256}")
    return {
        "status": "E_INTRINSIC_SNAPSHOT_V1_LEDGER_BUILT_OUTCOME_BLIND",
        "scope": "XAUUSD_M1_BUY_US_0800_1700_AMERICA_NEW_YORK",
        "future_price_outcomes_used": False,
        "source": {
            "path": str(source_path),
            "sha256": source_sha,
            "expected_sha256": expected_source_sha256,
        },
        "ledger": {
            "path": str(output_path),
            "sha256": sha256_file(output_path),
            "rows": int(len(ledger)),
            "episodes": int(ledger["episode_id"].nunique()),
            "snapshots": int(ledger["snapshot_time_utc"].nunique()),
            "first_snapshot_utc": str(ledger["snapshot_time_utc"].min()),
            "last_snapshot_utc": str(ledger["snapshot_time_utc"].max()),
        },
        "identity_rule": {
            "contiguous_snapshot_minutes": 5,
            "match": "overlap OR abs(center_old-center_new) <= 0.25*max(v_old,v_new)",
            "one_to_one": True,
            "slot_rank_is_not_quality": True,
            "new_identity_after_noncontiguous_snapshot": True,
        },
        "model_feature_whitelist": list(MODEL_FEATURE_WHITELIST),
        "intrinsic_model_row_eligibility": "current_family != Z4 AND origin_family != Z4",
        "explicitly_excluded_from_intrinsic_model": [
            "display_slot_rank", "upper_z4_count", "nearest_upper_z4_dist_v", "distance_v",
            "center", "zlo", "zhi", "v_snapshot", "is_new_episode", "family_changed",
            "center_shift_v", "zlo_shift_v", "zhi_shift_v"
        ],
    }


def run(candidates_path: Path, output_path: Path, manifest_path: Path, expected_source_sha256: str | None = None) -> tuple[pd.DataFrame, dict]:
    d = read_candidates(candidates_path)
    ledger = assign_episodes(d)
    write_deterministic_gzip(ledger, output_path)
    manifest = build_manifest(candidates_path, output_path, ledger, expected_source_sha256)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ledger, manifest


def main() -> None:
    a = parse_args()
    ledger, manifest = run(Path(a.candidates), Path(a.output), Path(a.manifest), a.expected_source_sha256)
    print(json.dumps({
        "status": manifest["status"],
        "rows": len(ledger),
        "episodes": ledger["episode_id"].nunique(),
        "ledger_sha256": manifest["ledger"]["sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
