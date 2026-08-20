#!/usr/bin/env python3
from __future__ import annotations
import argparse, concurrent.futures as cf, gzip, importlib.util, io, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v1',ROOT/'run_eurusd_propf_sprint_v1.py')
v1=importlib.util.module_from_spec(spec); spec.loader.exec_module(v1)
PIP=v1.PIP; HALF=0.5*PIP
TRAIN_END=pd.Timestamp('2015-12-31'); VAL_START=pd.Timestamp('2016-01-01'); VAL_END=pd.Timestamp('2018-12-31')


def load_dev(workers,out):
    items=list(v1.iso_week_urls(2012,2018)); frames=[]; cov=[]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs=[ex.submit(v1.fetch_week,it) for it in items]
        for fut in cf.as_completed(futs):
            y,w,df,status=fut.result(); cov.append({'year':y,'week':w,'status':status})
            if df is not None:
                try: frames.append(v1.normalize_week(df))
                except Exception as e: cov[-1]['status']=f'parse:{e}'
    pd.DataFrame(cov).sort_values(['year','week']).to_csv(out/'coverage.csv',index=False)
    d=pd.concat(frames,ignore_index=True).sort_values('utc').drop_duplicates('utc',keep='last')
    # Strict DEV date clip eliminates ISO-week spill into 2019.
    d=d[(d.utc>=pd.Timestamp('2012-01-01',tz='UTC'))&(d.utc<pd.Timestamp('2019-01-01',tz='UTC'))].copy()
    # Only retain UTC 00:00 through 11:05 for Asian/London experiment.
    mins=d.utc.dt.hour*60+d.utc.dt.minute; d=d[(mins>=0)&(mins<=11*60+5)].copy()
    d['mid_open']=(d.BidOpen+d.AskOpen)/2; d['mid_close']=(d.BidClose+d.AskClose)/2
    d['date']=d.utc.dt.tz_convert(None).dt.normalize()
    return d


def blocks5(g,start=7*60,end=10*60):
    x=g.copy(); m=x.utc.dt.hour*60+x.utc.dt.minute; x=x[(m>=start)&(m<end)].copy()
    if x.empty: return []
    x['bucket']=x.utc.dt.floor('5min')
    out=[]
    for b,z in x.groupby('bucket',sort=True):
        if len(z)<4: continue
        out.append({'start':b,'open_mid':float(z.iloc[0].mid_open),'close_mid':float(z.iloc[-1].mid_close),
                    'bid_high':float(z.BidHigh.max()),'bid_low':float(z.BidLow.min()),'ask_high':float(z.AskHigh.max()),'ask_low':float(z.AskLow.min()),
                    'next_time':b+pd.Timedelta(minutes=5)})
    return out


def prepare_days(d,range_mode):
    if range_mode=='FULL_ASIA': rs,re=0,6*60+59
    else: rs,re=5*60,6*60+59
    rows=[]
    for day,g in d.groupby('date',sort=True):
        if day.weekday()>=5: continue
        m=g.utc.dt.hour*60+g.utc.dt.minute
        rg=g[(m>=rs)&(m<=re)]
        if len(rg)<max(100,re-rs-5): continue
        hi=float(rg.AskHigh.max()); lo=float(rg.BidLow.min()); width=hi-lo
        b5=blocks5(g)
        if not b5: continue
        rows.append({'date':day,'range_hi':hi,'range_lo':lo,'range_width':width,'blocks':b5,'g':g})
    out=pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
    if not out.empty: out['med60_width']=out.range_width.shift(1).rolling(60,min_periods=60).median()
    return out


def row_at(g,t):
    z=g[g.utc==t]
    return None if len(z)!=1 else z.iloc[0]


def monitor(g,start,end):
    return g[(g.utc>=start)&(g.utc<end)][['utc','BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']].to_dict('records')


def simulate(day,arch,compress,rr):
    if not np.isfinite(day.med60_width) or day.med60_width<=0: return None
    if day.range_width>compress*day.med60_width: return None
    g=day.g; event=None
    for b in day.blocks:
        broke_up=b['ask_high']>day.range_hi; broke_dn=b['bid_low']<day.range_lo
        if arch=='BREAKOUT':
            up=b['close_mid']>day.range_hi; dn=b['close_mid']<day.range_lo
            if up and dn: continue
            if up: event=(1,b); break
            if dn: event=(-1,b); break
        else: # first sweep that closes back inside range
            if broke_up and broke_dn: continue
            if broke_up and b['close_mid']<day.range_hi: event=(-1,b); break
            if broke_dn and b['close_mid']>day.range_lo: event=(1,b); break
    if event is None: return None
    direction,b=event; ent=row_at(g,b['next_time'])
    if ent is None: return None
    end=pd.Timestamp(day.date,tz='UTC')+pd.Timedelta(hours=11)
    ex=row_at(g,end)
    if ex is None: return None
    bars=monitor(g,b['next_time'],end)
    # Stop is local to the event candle, never the far side of a large Asian range.
    anchor=b['bid_low'] if direction==1 else b['ask_high']
    sim=v1.simulate_trade(direction,float(ent.BidOpen),float(ent.AskOpen),anchor,bars,float(ex.BidOpen),float(ex.AskOpen),rr)
    if sim is None: return None
    return {'engine':f'LONDON_{arch}','date':day.date,'entry_utc':ent.utc,'direction':direction,'range_mode':None,'compress':compress,'rr':rr,
            'range_pips':day.range_width/PIP,'event_time':b['start'],**sim}


def gen(days,arch,compress,rr,range_mode):
    ts=[]
    for _,r in days.iterrows():
        z=simulate(r,arch,compress,rr)
        if z is not None: z['range_mode']=range_mode; ts.append(z)
    return pd.DataFrame(ts)


def mm(t,start,end): return v1.metrics(t[(t.date>=start)&(t.date<=end)]) if len(t) else v1.metrics(t)

def assess(t,meta):
    tr=mm(t,pd.Timestamp('2012-01-01'),TRAIN_END); va=mm(t,VAL_START,VAL_END)
    robust=(tr['n']>=40 and va['n']>=30 and tr['mean'] is not None and va['mean'] is not None and tr['mean']>0 and va['mean']>0 and tr['pf']>=1.08 and va['pf']>=1.08)
    score=min(tr['mean'],va['mean'])*math.sqrt(tr['n']+va['n']) if robust else -999
    allm=v1.metrics(t)
    return {**meta,'robust':robust,'score':score,'train_n':tr['n'],'train_mean':tr['mean'],'train_pf':tr['pf'],'train_dd':tr['max_dd'],'train_pos_years':tr['positive_years'],
            'val_n':va['n'],'val_mean':va['mean'],'val_pf':va['pf'],'val_dd':va['max_dd'],'val_pos_years':va['positive_years'],
            'n':allm['n'],'mean':allm['mean'],'pf':allm['pf'],'dd':allm['max_dd'],'positive_years':allm['positive_years']}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='eurusd-propf/results/dev_v3'); ap.add_argument('--workers',type=int,default=10)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    d=load_dev(a.workers,out)
    rows=[]; cand=[]
    for rm in ['FULL_ASIA','LATE_ASIA']:
        days=prepare_days(d,rm)
        for arch in ['BREAKOUT','SWEEP_FADE']:
            for comp in [0.75,1.0,1.25,1.5]:
                for rr in [1.0,1.5,2.0,2.5]:
                    t=gen(days,arch,comp,rr,rm); arow=assess(t,{'range_mode':rm,'arch':arch,'compress':comp,'rr':rr})
                    rows.append(arow); cand.append((arow,t))
    grid=pd.DataFrame(rows).sort_values(['robust','score'],ascending=[False,False]); grid.to_csv(out/'dev_v3_grid.csv',index=False)
    rb=[z for z in cand if z[0]['robust']]
    if not rb:
        result={'status':'EURUSD_PROPF_DEV_V3_NO_ROBUST_CANDIDATE','n_candidates':len(rows),'n_robust':0}
    else:
        rb.sort(key=lambda z:(-z[0]['score'],z[0]['range_mode'],z[0]['arch'],z[0]['compress'],z[0]['rr']))
        best,t=rb[0]; m=v1.metrics(t)
        quality=(m['n']>=120 and m['mean']>=0.10 and m['pf']>=1.20 and m['positive_years']>=5 and m['max_dd']<=15)
        t.to_csv(out/'selected_trades.csv',index=False)
        result={'status':'EURUSD_PROPF_DEV_V3_READY_TO_FREEZE' if quality else 'EURUSD_PROPF_DEV_V3_FAIL_QUALITY_GATE','n_candidates':len(rows),'n_robust':len(rb),'selected':best,'metrics':m,'quality_gate':quality}
    (out/'RESULT_DEV_V3.json').write_text(json.dumps(result,indent=2,default=str)); print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
