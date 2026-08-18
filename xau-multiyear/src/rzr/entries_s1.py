from __future__ import annotations
from copy import deepcopy
import numpy as np
VOL_FLOOR_K=(0.25,0.50,0.75,1.00)
def apply_volatility_floor(entry:dict,k:float)->dict|None:
    """Widen a structural stop so risk is at least k*causal sigma60; never tighten."""
    e=deepcopy(entry); sig=float(e.get('sigma60',np.nan)); ep=float(e.get('entry_price',np.nan)); stop0=float(e.get('stop_price',np.nan))
    if not (np.isfinite(sig) and sig>0 and np.isfinite(ep) and np.isfinite(stop0)):return None
    d=str(e.get('direction','')); risk0=ep-stop0 if d=='LONG' else stop0-ep if d=='SHORT' else np.nan
    if not np.isfinite(risk0) or risk0<=0:return None
    floor=float(k)*sig; risk=max(float(risk0),floor)
    if d=='LONG':stop=ep-risk; assert stop<=stop0+1e-12
    else:stop=ep+risk; assert stop>=stop0-1e-12
    e['structural_stop_price']=stop0; e['structural_risk_price']=float(risk0); e['vol_floor_k']=float(k); e['vol_floor_price']=float(floor); e['stop_price']=float(stop); e['risk_price']=float(risk); e['s1_widened']=bool(risk>risk0+1e-12)
    return e
