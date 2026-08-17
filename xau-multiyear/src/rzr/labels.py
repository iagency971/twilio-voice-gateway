from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ResearchConfig
from .types import ZoneSide


def label_contacts(bars: pd.DataFrame, contacts: pd.DataFrame, config: ResearchConfig, max_horizon_minutes: int = 120) -> pd.DataFrame:
    if contacts.empty:return contacts.copy()
    high=bars.high.to_numpy(float); low=bars.low.to_numpy(float); close=bars.close.to_numpy(float); volume=pd.to_numeric(bars.volume,errors="coerce").to_numpy(float) if "volume" in bars.columns else None; n=len(bars); recs=[]
    for c in contacts.to_dict("records"):
        i=int(c["contact_idx"]); side=ZoneSide(c["side"]); sig=float(c["sigma60"]); lo_z,up_z=float(c["lower"]),float(c["upper"]); contact_close=float(close[i]); end=min(n,i+max_horizon_minutes+1); h=high[i:end]; l=low[i:end]
        if side==ZoneSide.SUPPORT:favorable=h-max(contact_close,lo_z); adverse=max(contact_close,up_z)-l
        elif side==ZoneSide.RESISTANCE:favorable=min(contact_close,up_z)-l; adverse=h-min(contact_close,lo_z)
        else:
            expect_short=int(c.get("approach_direction",0))>0
            if expect_short:favorable=min(contact_close,up_z)-l; adverse=h-min(contact_close,lo_z)
            else:favorable=h-max(contact_close,lo_z); adverse=max(contact_close,up_z)-l
        mfe=float(np.nanmax(np.maximum(favorable,0.0))) if len(h) else np.nan; mae=float(np.nanmax(np.maximum(adverse,0.0))) if len(h) else np.nan; out=dict(c); out["mfe_sigma"]=mfe/sig if sig>0 else np.nan; out["mae_sigma"]=mae/sig if sig>0 else np.nan
        for threshold in config.reaction_thresholds:out[f"reaction_{str(threshold).replace('.', '_')}sigma"]=bool(out["mfe_sigma"]>=threshold)
        for minutes in config.failed_auction_minutes:
            e=min(n,i+minutes+1); cw=close[i:e]
            if side==ZoneSide.SUPPORT:reclaim=bool(np.any(cw>up_z))
            elif side==ZoneSide.RESISTANCE:reclaim=bool(np.any(cw<lo_z))
            else:reclaim=bool(np.any((cw>up_z)|(cw<lo_z)))
            out[f"failed_auction_{minutes}m"]=reclaim
        e5=min(n,i+config.acceptance_minutes); acceptance=False
        if e5-i>=config.acceptance_minutes:
            c5=close[i:e5]; h5=high[i:e5]; l5=low[i:e5]; tp=(h5+l5+c5)/3.0
            if volume is not None:
                v5=volume[i:e5]; vv=np.where(np.isfinite(v5),v5,0.0); vwap=float(np.sum(tp*vv)/np.sum(vv)) if float(np.sum(vv))>0 else float(np.mean(tp))
            else:vwap=float(np.mean(tp))
            if side==ZoneSide.SUPPORT:
                closes_beyond=int(np.sum(c5<lo_z)); earlier_reclaim=bool(np.any(c5[:-1]>up_z)) if len(c5)>1 else False; acceptance=closes_beyond>=config.acceptance_min_closes and vwap<lo_z and not earlier_reclaim
            elif side==ZoneSide.RESISTANCE:
                closes_beyond=int(np.sum(c5>up_z)); earlier_reclaim=bool(np.any(c5[:-1]<lo_z)) if len(c5)>1 else False; acceptance=closes_beyond>=config.acceptance_min_closes and vwap>up_z and not earlier_reclaim
        out["accepted_5m"]=bool(acceptance); out["behavior_primary"]="ACCEPTED" if acceptance else "REJECTED" if out[f"failed_auction_{config.failed_auction_primary_minutes}m"] else "UNRESOLVED"; recs.append(out)
    return pd.DataFrame.from_records(recs)
