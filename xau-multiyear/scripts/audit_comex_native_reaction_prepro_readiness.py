#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

FINAL_STATUS_SHA = "8a825b0bc1deba51959b78ab6e62206fe49232e76329558e83949bf6d3d4151a"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_markers(root: Path) -> dict[str, dict]:
    out = {}
    for p in root.rglob("*.json"):
        try:
            z = json.loads(p.read_text())
        except Exception:
            continue
        rid = z.get("market_request_id")
        raw = z.get("raw_file")
        if rid is None or raw in (None, ""):
            continue
        z = dict(z)
        z["_marker_path"] = str(p)
        raw_candidates = list(root.rglob(str(raw)))
        z["_raw_candidates"] = [str(x) for x in raw_candidates]
        out[str(rid)] = z
    return out


def parse_stage(x) -> int:
    if pd.isna(x):
        raise ValueError("contact stage missing")
    return int(float(x))


def within(ts: pd.Timestamp, start, end) -> bool:
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    if s.tzinfo is None:
        s = s.tz_localize("UTC")
    else:
        s = s.tz_convert("UTC")
    if e.tzinfo is None:
        e = e.tz_localize("UTC")
    else:
        e = e.tz_convert("UTC")
    return s <= ts < e


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--final-status", required=True)
    ap.add_argument("--stage1-resolution", required=True)
    ap.add_argument("--stage2-resolution", required=True)
    ap.add_argument("--stage3-resolution", required=True)
    ap.add_argument("--n1-root", required=True)
    ap.add_argument("--stage1-root", required=True)
    ap.add_argument("--stage2-root", required=True)
    ap.add_argument("--stage3-root", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    final_path = Path(args.final_status)
    if sha256_file(final_path) != FINAL_STATUS_SHA:
        raise SystemExit("final 368 contact-status SHA mismatch")

    final = pd.read_csv(final_path, dtype={"source_instrument_id": str})
    if len(final) != 368 or final.level_id.nunique() != 368:
        raise SystemExit("final status cardinality mismatch")
    contacts = final[final.exact_contact_final.astype(str).str.lower().eq("true")].copy()
    if len(contacts) != 238 or contacts.level_id.nunique() != 238:
        raise SystemExit("expected exactly 238 exact-contact events")
    contacts["t0"] = pd.to_datetime(contacts.first_exact_contact_time_utc, utc=True)
    contacts["stage"] = contacts.contact_stage.map(parse_stage)
    stage_counts = contacts.stage.value_counts().sort_index().to_dict()
    if stage_counts != {1: 231, 2: 6, 3: 1}:
        raise SystemExit(f"unexpected contact-stage counts {stage_counts}")

    s1 = pd.read_csv(args.stage1_resolution, dtype={"source_instrument_id": str})
    s2 = pd.read_csv(args.stage2_resolution, dtype={"source_instrument_id": str})
    s3 = pd.read_csv(args.stage3_resolution, dtype={"source_instrument_id": str})
    s1_map = s1.set_index("level_id")["stage1_market_request_id"].astype(str).to_dict()
    s2_map = s2.set_index("level_id")["stage2_market_request_id"].astype(str).to_dict()
    s3_map = s3.set_index("level_id")["stage3_market_request_id"].astype(str).to_dict()

    n1_markers = read_markers(Path(args.n1_root))
    st1_markers = read_markers(Path(args.stage1_root))
    st2_markers = read_markers(Path(args.stage2_root))
    st3_markers = read_markers(Path(args.stage3_root))

    # N1 should represent 92 complete J+1 raw-instrument session requests.
    n1_usable = []
    for rid, z in n1_markers.items():
        if str(z.get("schema")) != "ohlcv-1m":
            continue
        raws = z.get("_raw_candidates", [])
        if len(raws) == 1:
            n1_usable.append((rid, z, Path(raws[0])))
    if len(n1_usable) != 92:
        raise SystemExit(f"expected 92 usable N1 raw session blocks, found {len(n1_usable)}")

    missing_n1 = []
    missing_n2 = []
    integrity_fail = []
    n2_interval_fail = []
    contact_rows = []

    for r in contacts.itertuples(index=False):
        lid = str(r.level_id)
        iid = str(r.source_instrument_id)
        t0 = r.t0
        # Find the owned N1 session block containing the exact contact time on the same raw instrument.
        n1_matches = []
        for rid, z, raw in n1_usable:
            if str(z.get("symbols")) != iid:
                continue
            if within(t0, z.get("start"), z.get("end")):
                n1_matches.append((rid, z, raw))
        if len(n1_matches) != 1:
            missing_n1.append({"level_id": lid, "instrument_id": iid, "t0": t0.isoformat(), "matches": len(n1_matches)})
            n1_rid = ""
        else:
            n1_rid = n1_matches[0][0]

        stage = int(r.stage)
        if stage == 1:
            rid = s1_map.get(lid, "")
            marker = st1_markers.get(rid)
        elif stage == 2:
            rid = s2_map.get(lid, "")
            marker = st2_markers.get(rid)
        elif stage == 3:
            rid = s3_map.get(lid, "")
            marker = st3_markers.get(rid)
        else:
            raise SystemExit(f"invalid stage {stage} for {lid}")

        raw_path = None
        if not rid or marker is None or len(marker.get("_raw_candidates", [])) != 1:
            missing_n2.append({"level_id": lid, "stage": stage, "market_request_id": rid})
        else:
            raw_path = Path(marker["_raw_candidates"][0])
            expected_sha = marker.get("sha256")
            if expected_sha and sha256_file(raw_path) != expected_sha:
                integrity_fail.append({"level_id": lid, "stage": stage, "market_request_id": rid})
            if not within(t0, marker.get("start"), marker.get("end")):
                n2_interval_fail.append({"level_id": lid, "stage": stage, "market_request_id": rid, "t0": t0.isoformat()})

        contact_rows.append({
            "level_id": lid,
            "source_instrument_id": iid,
            "level_type": str(r.level_type),
            "contact_stage": stage,
            "t0": t0.isoformat(),
            "n1_market_request_id": n1_rid,
            "n2_market_request_id": rid,
            "n2_raw_present": raw_path is not None,
        })

    ok = not (missing_n1 or missing_n2 or integrity_fail or n2_interval_fail)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(contact_rows).to_csv(out / "contact_data_inventory.csv", index=False)

    result = {
        "version": "COMEX_DEV_RANK1_NATIVE_REACTION_PREPRO_READINESS_V0_9",
        "ready_for_pro_method_review": bool(ok),
        "reaction_outcomes_computed": False,
        "mfe_mae_computed": False,
        "market_data_api_called": False,
        "market_data_download_performed": False,
        "final_368_status_sha256": sha256_file(final_path),
        "native_levels": 368,
        "exact_contact_events": 238,
        "contact_stage_counts": {str(k): int(v) for k, v in stage_counts.items()},
        "n1_complete_session_blocks": len(n1_usable),
        "contacts_with_unique_n1_session_coverage": 238 - len(missing_n1),
        "contacts_with_n2_contact_raw_present": 238 - len(missing_n2),
        "n2_raw_integrity_failures": len(integrity_fail),
        "n2_contact_interval_failures": len(n2_interval_fail),
        "missing_n1": missing_n1,
        "missing_n2": missing_n2,
        "integrity_fail": integrity_fail,
        "n2_interval_fail": n2_interval_fail,
        "source_session_range_normalizer_provenance_audited": False,
        "notes": [
            "This audit checks file availability, mapping and raw-file integrity only.",
            "It deliberately does not decode post-contact price paths or calculate reaction outcomes.",
            "Source-session-range normalizer provenance remains a PRE-PRO/final-v1 QA item if Pro approves that normalizer."
        ],
    }
    (out / "readiness.json").write_text(json.dumps(result, indent=2))
    if not ok:
        raise SystemExit(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
