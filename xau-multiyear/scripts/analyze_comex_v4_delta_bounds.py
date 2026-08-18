#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
import numpy as np
import databento as db

SIDE_NONE={'N','None','nan','NaN','','0'}
HORIZONS=(1,5,15,30)

def load(p): return db.DBNStore.from_file(p).to_df(map_symbols=True).reset_index(drop=False)

def minute_frame(df):
    ts_col='ts_event' if 'ts_event' in df.columns else 'ts_recv'
    ts=pd.to_datetime(df[ts_col],utc=True,errors='coerce')
    side=df.side.astype(str); size=pd.to_numeric(df['size'],errors='coerce').fillna(0.0)
    x=pd.DataFrame({'minute':ts.dt.floor('min'),'B':np.where(side.eq('B'),size,0.0),'A':np.where(side.eq('A'),size,0.0),'N':np.where(side.isin(SIDE_NONE),size,0.0)})
    return x.groupby('minute',as_index=True)[['B','A','N']].sum().sort_index()

def stats_for(m,h):
    z=m.rolling(h,min_periods=1).sum() if h>1 else m.copy(); d=z.B-z.A; lo=d-z.N; hi=d+z.N; total=z.B+z.A+z.N
    active=total>0; robust=active&((lo>0)|(hi<0)); zero_or_amb=active&~robust
    return {'horizon_min':h,'active_windows':int(active.sum()),'robust_sign_windows':int(robust.sum()),'robust_sign_fraction':float(robust.sum()/active.sum()) if active.any() else None,'ambiguous_sign_windows':int(zero_or_amb.sum()),'mean_n_volume_share':float((z.N[active]/total[active]).mean()) if active.any() else None,'p95_n_volume_share':float((z.N[active]/total[active]).quantile(.95)) if active.any() else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw-root',required=True); ap.add_argument('--sessions',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); root=Path(a.raw_root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    s=pd.read_csv(a.sessions); era=dict(zip(s.research_trading_date.astype(str),s.era.astype(str))); rows=[]
    for date,e in era.items():
        f=list(root.rglob(f'{date}__trades.dbn.zst'))
        if len(f)!=1: raise SystemExit(f'expected one trades {date}, got {len(f)}')
        m=minute_frame(load(f[0]))
        for h in HORIZONS: rows.append({'era':e,'date':date,**stats_for(m,h)})
    d=pd.DataFrame(rows); d.to_csv(out/'delta_bounds_by_session.csv',index=False)
    byera=[]
    for (e,h),g in d.groupby(['era','horizon_min'],sort=True):
        active=int(g.active_windows.sum()); robust=int(g.robust_sign_windows.sum()); amb=int(g.ambiguous_sign_windows.sum())
        byera.append({'era':e,'horizon_min':int(h),'active_windows':active,'robust_sign_windows':robust,'robust_sign_fraction':robust/active if active else None,'ambiguous_sign_windows':amb})
    overall=[]
    for h,g in d.groupby('horizon_min',sort=True):
        active=int(g.active_windows.sum()); robust=int(g.robust_sign_windows.sum()); overall.append({'horizon_min':int(h),'active_windows':active,'robust_sign_fraction':robust/active if active else None})
    result={'version':'COMEX_V4_PILOT12_DELTA_BOUNDS_V1','market_data_download_performed':False,'source':'existing paid trades pilot artifact','definition':'delta_min=B-A-N; delta_max=B-A+N; sign robust if interval excludes zero','overall':overall,'by_era':byera,'decision_note':'No N-side imputation is required when the delta interval has a robust sign; ambiguous windows remain explicitly uncertain.'}
    (out/'delta_bounds_summary.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
