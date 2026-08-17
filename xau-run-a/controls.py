from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ResearchConfig
from .features import session_bucket


def generate_matched_controls(bars: pd.DataFrame, contacts: pd.DataFrame, zones: pd.DataFrame,
                              config: ResearchConfig, controls_per_contact: int = 1,
                              sigma_tolerance: float = 0.20) -> pd.DataFrame:
    """
    Matched arbitrary-price/time controls.

    For each real contact, sample another M1 timestamp in the same session and with
    comparable sigma60. The control center is the observed close at that timestamp,
    and the candidate is rejected if that price is near any real zone already known.
    This estimates how often price produces an apparent reaction at an arbitrary
    matched time/price, rather than at a detected zone.
    """
    if contacts.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(config.control_seed)
    bars = bars.copy()
    if "sigma60" not in bars.columns:
        raise ValueError("bars must include sigma60 for matched controls")
    bars["session"] = [session_bucket(ts, config.timezone) for ts in bars.index]
    rows = []
    known_zones = zones.copy() if not zones.empty else pd.DataFrame(columns=["known_time","lower","upper"])

    for _, c in contacts.iterrows():
        sig = float(c.sigma60)
        if not np.isfinite(sig) or sig <= 0:
            continue
        session = c.session
        width = float(c.upper - c.lower)
        pool = bars[(bars.session == session) & bars.sigma60.notna()]
        pool = pool[(pool.sigma60 >= sig * (1-sigma_tolerance)) & (pool.sigma60 <= sig * (1+sigma_tolerance))]
        # Do not sample within 60 minutes of the real contact itself.
        pool = pool[np.abs((pool.index - pd.Timestamp(c.contact_time)).total_seconds()) >= 3600]
        if pool.empty:
            continue
        positions = rng.permutation(len(pool))
        made = 0
        for pos in positions:
            ts = pool.index[int(pos)]
            px = float(pool.close.iloc[int(pos)])
            known = known_zones[known_zones.known_time <= ts] if len(known_zones) else known_zones
            if len(known):
                margin = max(width, config.point_zone_sigma_mult * sig) * 2.0
                near = ((px >= known.lower - margin) & (px <= known.upper + margin)).any()
                if near:
                    continue
            idx = int(bars.index.get_loc(ts))
            approach = 0
            if idx > 0:
                j = max(0, idx-5)
                d = float(bars.close.iloc[idx-1] - bars.close.iloc[j])
                approach = 1 if d > 0 else -1 if d < 0 else 0
            rows.append({
                "zone_id": f"CTRL_{len(rows):08d}",
                "matched_to_zone_id": c.zone_id,
                "family": "CONTROL",
                "variant": "MATCHED_ARBITRARY_TIME_PRICE",
                "side": "NEUTRAL",
                "zone_known_time": ts,
                "contact_time": ts,
                "contact_idx": idx,
                "lower": px-width/2,
                "upper": px+width/2,
                "center": px,
                "penetration_depth": 0.5,
                "sigma60": float(pool.sigma60.iloc[int(pos)]),
                "approach_direction": approach,
                "session": session,
            })
            made += 1
            if made >= controls_per_contact:
                break
    return pd.DataFrame.from_records(rows)
