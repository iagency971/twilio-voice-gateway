#!/usr/bin/env python3
from __future__ import annotations

import argparse, json
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import databento as db

NY=ZoneInfo('America/New_York')
SIDE_NONE={'N','None','nan','NaN','','0'}
EPS=1e-9


def load(path):
    return db.DBNStore.from_file(path).to_df(map_symbols=True).reset_index(drop=False)


def tick_prediction(px: pd.Series) -> pd.Series:
    d=px.diff()
    sign=pd.Series(np.where(d>EPS,1,np.where(d<-EPS,-1,np.nan)),index=px.index,dtype=float).ffill()
    out=pd.Series('N',index=px.index,dtype=object)
    out.loc[sign>0]='B'; out.loc[sign<0]='A'
    return out


def predictions(df:pd.DataFrame):
    px=pd.to_numeric(df.price,errors='coerce')
    bid=pd.to_numeric(df.bid_px_00,errors='coerce')
    ask=pd.to_numeric(df.ask_px_00,errors='coerce')
    valid=px.notna()&bid.notna()&ask.notna()&(bid>0)&(ask>0)&(bid<ask)
    mid=(bid+ask)/2
    tick=tick_prediction(px)
    rules={}
    # high precision / lower coverage
    sell=valid&(px<=bid+EPS); buy=valid&(px>=ask-EPS)
    r=pd.Series('N',index=df.index,dtype=object); r.loc[sell&~buy]='A'; r.loc[buy&~sell]='B'; rules['touch_only']=r
    # quote rule: classify by side of midpoint
    r=pd.Series('N',index=df.index,dtype=object); r.loc[valid&(px<mid-EPS)]='A'; r.loc[valid&(px>mid+EPS)]='B'; rules['midquote']=r
    # midquote plus tick test only for exact-midquote trades
    r=rules['midquote'].copy(); tie=valid&r.eq('N')&(px.sub(mid).abs()<=EPS); r.loc[tie]=tick.loc[tie]; rules['midquote_tick']=r
    # touch first, then midpoint, then tick for remaining valid-BBO records
    r=rules['touch_only'].copy(); rem=valid&r.eq('N'); r.loc[rem&(px<mid-EPS)]='A'; r.loc[rem&(px>mid+EPS)]='B'; rem2=valid&r.eq('N'); r.loc[rem2]=tick.loc[rem2]; rules['quote_tick_full']=r
    return rules,valid


def score(native:pd.Series,pred:pd.Series,mask:pd.Series):
    known=mask&native.isin(['A','B']); cls=known&pred.isin(['A','B']); ok=cls&native.eq(pred)
    return {'known':int(known.sum()),'classified':int(cls.sum()),'coverage':float(cls.sum()/known.sum()) if known.any() else None,'correct':int(ok.sum()),'accuracy':float(ok.sum()/cls.sum()) if cls.any() else None}


def n_recovery(native,pred,mask):
    n=mask&native.isin(SIDE_NONE); cls=n&pred.isin(['A','B'])
    return {'n_valid':int(n.sum()),'classified':int(cls.sum()),'coverage':float(cls.sum()/n.sum()) if n.any() else None,'pred_A':int((cls&pred.eq('A')).sum()),'pred_B':int((cls&pred.eq('B')).sum()),'unclassified':int((n&~pred.isin(['A','B'])).sum())}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw-root',required=True); ap.add_argument('--sessions',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    root=Path(a.raw_root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    sess=pd.read_csv(a.sessions); era=dict(zip(sess.research_trading_date.astype(str),sess.era.astype(str)))
    rows=[]; hour_rows=[]
    for date,e in era.items():
        files=list(root.rglob(f'{date}__tbbo.dbn.zst'))
        if len(files)!=1: raise SystemExit(f'expected one TBBO for {date}, got {len(files)}')
        df=load(files[0]); native=df.side.astype(str); rules,valid=predictions(df)
        for name,pred in rules.items():
            s=score(native,pred,valid); nr=n_recovery(native,pred,valid)
            rows.append({'era':e,'date':date,'rule':name,**s,**{f'n_{k}':v for k,v in nr.items()}})
        # N-side temporal concentration, using event time where available.
        ts_col='ts_event' if 'ts_event' in df.columns else ('ts_recv' if 'ts_recv' in df.columns else None)
        if ts_col:
            ts=pd.to_datetime(df[ts_col],utc=True,errors='coerce').dt.tz_convert(NY)
            n=native.isin(SIDE_NONE)
            z=pd.DataFrame({'hour':ts.dt.hour,'is_n':n.astype(int)}).dropna()
            for h,g in z.groupby('hour'):
                hour_rows.append({'era':e,'date':date,'hour_ny':int(h),'records':int(len(g)),'n_side':int(g.is_n.sum())})
    d=pd.DataFrame(rows); d.to_csv(out/'side_rule_by_session.csv',index=False)
    hr=pd.DataFrame(hour_rows)
    if len(hr): hr.groupby('hour_ny',as_index=False)[['records','n_side']].sum().assign(n_rate=lambda x:x.n_side/x.records).to_csv(out/'n_side_by_local_hour.csv',index=False)
    summary=[]
    for rule,g in d.groupby('rule',sort=True):
        known=int(g.known.sum()); cls=int(g.classified.sum()); correct=int(g.correct.sum()); nv=int(g.n_n_valid.sum()); nc=int(g.n_classified.sum())
        summary.append({'rule':rule,'known':known,'classified':cls,'coverage':cls/known if known else None,'correct':correct,'accuracy':correct/cls if cls else None,'n_valid':nv,'n_classified':nc,'n_recovery_coverage':nc/nv if nv else None})
    era_summary=[]
    for (e,rule),g in d.groupby(['era','rule'],sort=True):
        known=int(g.known.sum()); cls=int(g.classified.sum()); correct=int(g.correct.sum()); nv=int(g.n_n_valid.sum()); nc=int(g.n_classified.sum())
        era_summary.append({'era':e,'rule':rule,'coverage':cls/known if known else None,'accuracy':correct/cls if cls else None,'n_recovery_coverage':nc/nv if nv else None,'known':known,'n_valid':nv})
    result={'version':'COMEX_V4_PILOT12_SIDE_RULES_V1','market_data_download_performed':False,'source':'existing paid TBBO pilot artifact','rules':summary,'by_era':era_summary,'decision_note':'Rule selection must be frozen before any larger acquisition; native N is retained as an explicit missingness/auction-type feature rather than silently discarded.'}
    (out/'side_rule_summary.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
