from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ResearchConfig
from .types import ZoneSide


def classify_behavior_v2(
    bars: pd.DataFrame,
    contacts: pd.DataFrame,
    config: ResearchConfig,
) -> pd.DataFrame:
    """Classify the post-contact auction path without changing Phase-A reaction labels.

    CLEAN_REJECTION:
        price reclaims the proximal edge before ever breaching the distal edge.
    FAILED_AUCTION:
        price first breaches the distal edge and subsequently reclaims the proximal edge
        within ``failed_auction_primary_minutes``.
    ACCEPTED_BREAK:
        the existing preregistered 5-minute acceptance rule is satisfied beyond the distal edge.
    UNRESOLVED:
        none of the above is confirmed.

    The function is causal with respect to the chosen confirmation windows and records the
    confirmation delays explicitly.  It does not use future information to alter the zone.
    """
    if contacts.empty:
        return contacts.copy()

    high = bars.high.to_numpy(float)
    low = bars.low.to_numpy(float)
    close = bars.close.to_numpy(float)
    volume = (
        pd.to_numeric(bars.volume, errors="coerce").to_numpy(float)
        if "volume" in bars.columns
        else None
    )
    n = len(bars)
    primary_minutes = int(config.failed_auction_primary_minutes)
    recs = []

    for c in contacts.to_dict("records"):
        out = dict(c)
        i = int(c["contact_idx"])
        side = ZoneSide(c["side"])
        sig = float(c.get("sigma60", np.nan))
        lo_z = float(c["lower"])
        up_z = float(c["upper"])

        # Resolve a neutral zone direction mechanically from the approach, exactly as Phase A.
        if side == ZoneSide.NEUTRAL:
            expect_short = int(c.get("approach_direction", 0)) > 0
            side_eff = ZoneSide.RESISTANCE if expect_short else ZoneSide.SUPPORT
        else:
            side_eff = side

        end = min(n, i + primary_minutes + 1)
        h = high[i:end]
        l = low[i:end]
        cw = close[i:end]

        if side_eff == ZoneSide.SUPPORT:
            breach_mask = l < lo_z
            reclaim_mask = cw > up_z
            overshoot = np.maximum(lo_z - l, 0.0)
        else:
            breach_mask = h > up_z
            reclaim_mask = cw < lo_z
            overshoot = np.maximum(h - up_z, 0.0)

        breach_idx = np.flatnonzero(breach_mask)
        reclaim_idx = np.flatnonzero(reclaim_mask)
        first_breach = int(breach_idx[0]) if len(breach_idx) else None
        first_reclaim = int(reclaim_idx[0]) if len(reclaim_idx) else None

        clean_rejection = bool(
            first_reclaim is not None
            and (first_breach is None or first_reclaim < first_breach)
        )

        failed_auction = False
        reclaim_after_breach = None
        if first_breach is not None:
            later_reclaims = reclaim_idx[reclaim_idx >= first_breach]
            if len(later_reclaims):
                reclaim_after_breach = int(later_reclaims[0])
                failed_auction = True

        # Preserve the preregistered Phase-A acceptance definition, but expose it as ACCEPTED_BREAK.
        e5 = min(n, i + int(config.acceptance_minutes))
        acceptance = False
        if e5 - i >= int(config.acceptance_minutes):
            c5 = close[i:e5]
            h5 = high[i:e5]
            l5 = low[i:e5]
            typical = (h5 + l5 + c5) / 3.0
            if volume is not None:
                v5 = volume[i:e5]
                vv = np.where(np.isfinite(v5), v5, 0.0)
                vwap = (
                    float(np.sum(typical * vv) / np.sum(vv))
                    if float(np.sum(vv)) > 0
                    else float(np.mean(typical))
                )
            else:
                vwap = float(np.mean(typical))

            if side_eff == ZoneSide.SUPPORT:
                closes_beyond = int(np.sum(c5 < lo_z))
                earlier_reclaim = bool(np.any(c5[:-1] > up_z)) if len(c5) > 1 else False
                acceptance = bool(
                    closes_beyond >= int(config.acceptance_min_closes)
                    and vwap < lo_z
                    and not earlier_reclaim
                )
            else:
                closes_beyond = int(np.sum(c5 > up_z))
                earlier_reclaim = bool(np.any(c5[:-1] < lo_z)) if len(c5) > 1 else False
                acceptance = bool(
                    closes_beyond >= int(config.acceptance_min_closes)
                    and vwap > up_z
                    and not earlier_reclaim
                )

        # Acceptance is a stronger early confirmation and, by construction, contains no earlier reclaim.
        if acceptance:
            behavior = "ACCEPTED_BREAK"
        elif failed_auction:
            behavior = "FAILED_AUCTION"
        elif clean_rejection:
            behavior = "CLEAN_REJECTION"
        else:
            behavior = "UNRESOLVED"

        out["behavior_v2"] = behavior
        out["distal_breach_v2"] = bool(first_breach is not None)
        out["clean_rejection_v2"] = clean_rejection
        out["failed_auction_v2"] = failed_auction
        out["accepted_break_v2"] = bool(acceptance)
        out["first_breach_minutes_v2"] = first_breach if first_breach is not None else np.nan
        out["first_reclaim_minutes_v2"] = first_reclaim if first_reclaim is not None else np.nan
        out["reclaim_after_breach_minutes_v2"] = (
            reclaim_after_breach if reclaim_after_breach is not None else np.nan
        )
        max_overshoot = float(np.nanmax(overshoot)) if len(overshoot) else 0.0
        out["max_distal_overshoot_sigma_v2"] = (
            max_overshoot / sig if np.isfinite(sig) and sig > 0 else np.nan
        )
        recs.append(out)

    return pd.DataFrame.from_records(recs)
