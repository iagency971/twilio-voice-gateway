#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v1", ROOT/"run_eurusd_propf_sprint_v1.py")
v1=importlib.util.module_from_spec(spec); spec.loader.exec_module(v1)
PIP=v1.PIP
TRAIN_END=pd.Timestamp("2015-12-31")
VAL_START=pd.Timestamp("2016-01-01")
VAL_END=pd.Timestamp("2018-12-31")


def exact(g,col,h,m): return v1.exact_row(g,col,h,m)
def win(g,col,a,b): return v1.window(g,col,a,b)

def build_event_fade_days(d, entry_minute):
    rows=[]; x=d.copy(); x['local_date']=x.ny.dt.date
    eh=8; em=entry_minute
    prev_total=eh*60+em-1; ph=prev_total//60; pm=prev_total%60
    for day,g in x.groupby('local_date',sort=True):
        if pd.Timestamp(day).weekday()>=5: continue
        r0830=exact(g,'ny',8,30); rprev=exact(g,'ny',ph,pm); rent=exact(g,'ny',eh,em)
        r0930=exact(g,'ny',9,30); r1030=exact(g,'ny',10,30)
        sw=win(g,'ny',(8,30),(ph,pm))
        bars0930=win(g,'ny',(eh,em),(9,29)); bars1030=win(g,'ny',(eh,em),(10,29))
        if any(z is None for z in [r0830,rprev,rent,r0930,r1030]) or len(sw)<max(3,entry_minute-30-1): continue
        impulse=float(rprev.mid_close-r0830.mid_open)
        rows.append({'date':pd.Timestamp(day),'impulse':impulse,'entry_utc':rent.utc,'entry_bid':float(rent.BidOpen),'entry_ask':float(rent.AskOpen),
                     'long_stop_anchor':float(sw.BidLow.min()),'short_stop_anchor':float(sw.AskHigh.max()),
                     'exit0930_bid':float(r0930.BidOpen),'exit0930_ask':float(r0930.AskOpen),'exit1030_bid':float(r1030.BidOpen),'exit1030_ask':float(r1030.AskOpen),
                     'bars0930':bars0930[['utc','BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']].to_dict('records'),
                     'bars1030':bars1030[['utc','BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']].to_dict('records')})
    out=pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
    if not out.empty: out['med60']=out.impulse.abs().shift(1).rolling(60,min_periods=60).median()
    return out


def gen_event_fade(days,q,rr,time_exit):
    ts=[]
    for _,r in days.iterrows():
        if not np.isfinite(r.med60) or r.med60<=0 or r.impulse==0: continue
        if abs(r.impulse)<q*r.med60: continue
        direction=-1 if r.impulse>0 else 1
        anchor=r.long_stop_anchor if direction==1 else r.short_stop_anchor
        bars=r.bars0930 if time_exit=='0930' else r.bars1030
        eb=r.exit0930_bid if time_exit=='0930' else r.exit1030_bid
        ea=r.exit0930_ask if time_exit=='0930' else r.exit1030_ask
        sim=v1.simulate_trade(direction,r.entry_bid,r.entry_ask,anchor,bars,eb,ea,rr)
        if sim is None: continue
        ts.append({'engine':'EVENT_FADE','date':r.date,'entry_utc':r.entry_utc,'direction':direction,'q':q,'rr':rr,'time_exit':time_exit,**sim})
    return pd.DataFrame(ts)


def build_session_turn_days(d):
    rows=[]; x=d.copy(); x['utc_date']=x.utc.dt.date
    for day,g in x.groupby('utc_date',sort=True):
        if pd.Timestamp(day).weekday()>=5: continue
        # Fixed UTC clock, deliberately avoiding DST ambiguity.
        r0700=g[(g.utc.dt.hour==7)&(g.utc.dt.minute==0)]
        r1259=g[(g.utc.dt.hour==12)&(g.utc.dt.minute==59)]
        r1305=g[(g.utc.dt.hour==13)&(g.utc.dt.minute==5)]
        r1600=g[(g.utc.dt.hour==16)&(g.utc.dt.minute==0)]
        r1800=g[(g.utc.dt.hour==18)&(g.utc.dt.minute==0)]
        if any(len(z)!=1 for z in [r0700,r1259,r1305,r1600,r1800]): continue
        a=r0700.iloc[0]; b=r1259.iloc[0]; e=r1305.iloc[0]; x16=r1600.iloc[0]; x18=r1800.iloc[0]
        sw=g[((g.utc.dt.hour*60+g.utc.dt.minute)>=12*60+30)&((g.utc.dt.hour*60+g.utc.dt.minute)<=13*60+4)]
        bars16=g[((g.utc.dt.hour*60+g.utc.dt.minute)>=13*60+5)&((g.utc.dt.hour*60+g.utc.dt.minute)<=15*60+59)]
        bars18=g[((g.utc.dt.hour*60+g.utc.dt.minute)>=13*60+5)&((g.utc.dt.hour*60+g.utc.dt.minute)<=17*60+59)]
        if len(sw)<30: continue
        move=float(b.mid_close-a.mid_open)
        rows.append({'date':pd.Timestamp(day),'move':move,'entry_utc':e.utc,'entry_bid':float(e.BidOpen),'entry_ask':float(e.AskOpen),'stop_anchor':float(sw.BidLow.min()),
                     'exit16_bid':float(x16.BidOpen),'exit18_bid':float(x18.BidOpen),
                     'bars16':bars16[['utc','BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']].to_dict('records'),
                     'bars18':bars18[['utc','BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']].to_dict('records')})
    out=pd.DataFrame(rows).sort_values('date').reset_index(drop=True)
    if not out.empty: out['med60']=out.move.abs().shift(1).rolling(60,min_periods=60).median()
    return out


def gen_session_turn(days,q,rr,time_exit):
    ts=[]
    for _,r in days.iterrows():
        if not np.isfinite(r.med60) or r.med60<=0 or r.move>=0: continue
        if abs(r.move)<q*r.med60: continue
        bars=r.bars16 if time_exit=='1600' else r.bars18
        eb=r.exit16_bid if time_exit=='1600' else r.exit18_bid
        sim=v1.simulate_trade(1,r.entry_bid,r.entry_ask,r.stop_anchor,bars,eb,np.nan,rr)
        if sim is None: continue
        ts.append({'engine':'SESSION_TURN','date':r.date,'entry_utc':r.entry_utc,'direction':1,'q':q,'rr':rr,'time_exit':time_exit,**sim})
    return pd.DataFrame(ts)


def side_metrics(t, start, end):
    if t.empty: return v1.metrics(t)
    return v1.metrics(t[(t.date>=start)&(t.date<=end)])


def eval_candidate(t, meta):
    tr=side_metrics(t,pd.Timestamp('2012-01-01'),TRAIN_END)
    va=side_metrics(t,VAL_START,VAL_END)
    robust=(tr['n']>=30 and va['n']>=20 and tr['mean'] is not None and va['mean'] is not None and tr['mean']>0 and va['mean']>0 and tr['pf']>1.05 and va['pf']>1.05)
    minmean=min(tr['mean'],va['mean']) if tr['mean'] is not None and va['mean'] is not None else -999
    score=minmean*math.sqrt(tr['n']+va['n']) if robust else -999
    return {**meta,'robust':robust,'score':score,
            'train_n':tr['n'],'train_mean':tr['mean'],'train_pf':tr['pf'],'train_dd':tr['max_dd'],'train_pos_years':tr['positive_years'],
            'val_n':va['n'],'val_mean':va['mean'],'val_pf':va['pf'],'val_dd':va['max_dd'],'val_pos_years':va['positive_years'],
            'all_n':len(t),'all_mean':float(t.net_r_base.mean()) if len(t) else None,'all_pf':v1.pf(t.net_r_base) if len(t) else 0}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='eurusd-propf/results/dev_v2'); ap.add_argument('--workers',type=int,default=10)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    # DEV ONLY. OOS years are never downloaded by this script.
    d,cov=v1.load_fxcm(2012,2018,a.workers,out)
    rows=[]; candidates=[]
    for entry in [35,40,45]:
        days=build_event_fade_days(d,entry)
        for q in [1.0,1.5,2.0,2.5]:
            for rr in [1.0,1.5,2.0]:
                for te in ['0930','1030']:
                    t=gen_event_fade(days,q,rr,te)
                    ev=eval_candidate(t,{'engine':'EVENT_FADE','entry_minute':entry,'q':q,'rr':rr,'time_exit':te})
                    rows.append(ev); candidates.append((ev,t))
    sd=build_session_turn_days(d)
    for q in [0.5,1.0,1.5,2.0]:
        for rr in [1.0,1.5,2.0]:
            for te in ['1600','1800']:
                t=gen_session_turn(sd,q,rr,te)
                ev=eval_candidate(t,{'engine':'SESSION_TURN','entry_minute':1305,'q':q,'rr':rr,'time_exit':te})
                rows.append(ev); candidates.append((ev,t))
    grid=pd.DataFrame(rows).sort_values(['robust','score'],ascending=[False,False]); grid.to_csv(out/'dev_v2_grid.csv',index=False)
    robust=[(e,t) for e,t in candidates if e['robust']]
    if not robust:
        result={'status':'EURUSD_PROPF_DEV_V2_NO_ROBUST_CANDIDATE','n_candidates':len(rows),'n_robust':0}
    else:
        robust.sort(key=lambda z:(-z[0]['score'], z[0]['engine'], z[0]['entry_minute'], z[0]['q'], z[0]['rr'], z[0]['time_exit']))
        best,bestt=robust[0]
        # Extra DEV-only quality gate before reserving V2 for OOS.
        allm=v1.metrics(bestt)
        eligible=(allm['n']>=80 and allm['mean']>=0.10 and allm['pf']>=1.20 and allm['positive_years']>=5 and allm['max_dd']<=15)
        bestt.to_csv(out/'dev_v2_selected_trades.csv',index=False)
        result={'status':'EURUSD_PROPF_DEV_V2_READY_TO_FREEZE' if eligible else 'EURUSD_PROPF_DEV_V2_FAIL_QUALITY_GATE','n_candidates':len(rows),'n_robust':len(robust),'selected':best,'selected_all_metrics':allm,'quality_gate':eligible}
    (out/'RESULT_DEV_V2.json').write_text(json.dumps(result,indent=2,default=str))
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
