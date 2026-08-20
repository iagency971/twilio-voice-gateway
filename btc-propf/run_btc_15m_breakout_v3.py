#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v1', ROOT/'run_btc_session_momentum_v1.py')
v1=importlib.util.module_from_spec(spec); spec.loader.exec_module(v1)

CANDS=[('L16_RAW',16,False),('L32_RAW',32,False),('L16_RSI',16,True),('L32_RSI',32,True)]
ATR_N=14; ATR_MULT=1.5; RR=2.0; MAX_HOLD=16


def build_15m(d):
    x=d.set_index('utc').sort_index()
    b=x.resample('15min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),count=('close','count'))
    b=b[b['count']==3].drop(columns='count').dropna().copy()
    prev=b.close.shift(1)
    tr=pd.concat([(b.high-b.low),(b.high-prev).abs(),(b.low-prev).abs()],axis=1).max(axis=1)
    b['atr14']=tr.ewm(alpha=1/ATR_N,adjust=False,min_periods=ATR_N).mean()
    for L in [16,32]:
        b[f'dch_{L}']=b.high.shift(1).rolling(L,min_periods=L).max()
        b[f'dcl_{L}']=b.low.shift(1).rolling(L,min_periods=L).min()
    daily=b.resample('1D').agg(close=('close','last'),n=('close','count'))
    daily=daily[daily.n>=90].copy()
    delta=daily.close.diff(); gain=delta.clip(lower=0); loss=(-delta.clip(upper=0))
    ag=gain.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); al=loss.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    rs=ag/al.replace(0,np.nan); rsi=100-(100/(1+rs)); rsi[(al==0)&(ag>0)]=100; rsi[(al==0)&(ag==0)]=50
    prior=rsi.shift(1)
    b['day']=b.index.floor('D'); b['prior_day_rsi14']=b['day'].map(prior)
    return b


def metrics(tr):
    if tr.empty: return {'n':0,'mean':None,'sum':0.0,'pf':None,'max_dd':None,'positive_years':0,'active_years':0,'losing_streak':None}
    tr=tr.sort_values('entry_time').copy(); r=tr.net_R.astype(float).to_numpy(); pos=r[r>0].sum(); neg=-r[r<0].sum()
    pf=float(pos/neg) if neg>0 else (float('inf') if pos>0 else None)
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]; dd=np.maximum(peak-eq,0)
    cur=streak=0
    for v in r:
        if v<0: cur+=1; streak=max(streak,cur)
        else: cur=0
    y=tr.assign(year=pd.to_datetime(tr.entry_time,utc=True).dt.year).groupby('year').net_R.sum()
    return {'n':int(len(r)),'mean':float(r.mean()),'sum':float(r.sum()),'pf':pf,'max_dd':float(dd.max(initial=0.0)),
            'positive_years':int((y>0).sum()),'active_years':int(len(y)),'losing_streak':int(streak),
            'annual':{str(int(k)):float(v) for k,v in y.items()}}


def simulate(b,L,use_rsi,start,end,fee_bp_side):
    start=pd.Timestamp(start,tz='UTC'); end=pd.Timestamp(end,tz='UTC')
    idx=b.index; rows=[]; i=max(1,idx.searchsorted(start))
    last=min(len(b)-1,idx.searchsorted(end)-1)
    while i<=last:
        entry_time=idx[i]
        if entry_time<start or entry_time>=end or entry_time+pd.Timedelta(hours=4)>end:
            i+=1; continue
        s=b.iloc[i-1]
        if pd.isna(s.atr14) or pd.isna(s[f'dch_{L}']) or pd.isna(s[f'dcl_{L}']):
            i+=1; continue
        side=0
        if s.close>s[f'dch_{L}']: side=1
        elif s.close<s[f'dcl_{L}']: side=-1
        if side==0:
            i+=1; continue
        if use_rsi:
            rsi=s.prior_day_rsi14
            if pd.isna(rsi) or (side==1 and not rsi>50) or (side==-1 and not rsi<50):
                i+=1; continue
        entry=float(b.iloc[i].open); dist=ATR_MULT*float(s.atr14)
        if not np.isfinite(dist) or dist<=0:
            i+=1; continue
        stop=entry-side*dist; target=entry+side*RR*dist
        exit_px=None; reason=None; exit_i=None
        for j in range(i,min(i+MAX_HOLD,last+1)):
            bar=b.iloc[j]; o,h,l,c=map(float,[bar.open,bar.high,bar.low,bar.close])
            if j>i:
                if side==1 and o<=stop: exit_px=o; reason='SL_GAP'; exit_i=j; break
                if side==-1 and o>=stop: exit_px=o; reason='SL_GAP'; exit_i=j; break
                if side==1 and o>=target: exit_px=target; reason='TP_GAP_CAPPED'; exit_i=j; break
                if side==-1 and o<=target: exit_px=target; reason='TP_GAP_CAPPED'; exit_i=j; break
            hit_sl=(l<=stop) if side==1 else (h>=stop)
            hit_tp=(h>=target) if side==1 else (l<=target)
            if hit_sl:
                exit_px=stop; reason='SL_AMBIG' if hit_tp else 'SL'; exit_i=j; break
            if hit_tp:
                exit_px=target; reason='TP'; exit_i=j; break
        if exit_px is None:
            exit_i=min(i+MAX_HOLD-1,last); exit_px=float(b.iloc[exit_i].close); reason='TIME'
        gross=side*(exit_px-entry)/dist
        cost=(fee_bp_side/10000.0)*(entry+exit_px)/dist
        rows.append({'entry_time':str(entry_time),'exit_time':str(idx[exit_i]),'side':'LONG' if side==1 else 'SHORT',
                     'entry':entry,'stop':stop,'target':target,'atr_signal':float(s.atr14),'stop_dist':dist,'reason':reason,
                     'gross_R':gross,'net_R':gross-cost,'prior_day_rsi14':None if pd.isna(s.prior_day_rsi14) else float(s.prior_day_rsi14)})
        i=exit_i+1  # one position at a time; no same-bar re-entry
    return pd.DataFrame(rows)


def main():
    out=Path('btc-propf/results/breakout_v3'); out.mkdir(parents=True,exist_ok=True)
    try:
        d,diag=v1.load_data(out); b=build_15m(d)
        diag.update({'bars_15m':int(len(b)),'bars_15m_min':str(b.index.min()),'bars_15m_max':str(b.index.max())})
        (out/'data_diagnostics.json').write_text(json.dumps(diag,indent=2))
        grid=[]; trains={}
        for name,L,use_rsi in CANDS:
            tr=simulate(b,L,use_rsi,'2019-01-01','2023-01-01',v1.COSTS['PRIMARY']); trains[name]=tr
            m=metrics(tr)
            eligible=(m['n']>=250 and m['mean'] is not None and m['mean']>=0.08 and m['pf'] is not None and m['pf']>=1.15
                      and m['positive_years']>=3 and m['max_dd'] is not None and m['max_dd']<=20.0)
            score=m['mean']*math.sqrt(m['n']) if eligible else -999.0
            grid.append({'candidate':name,'L':L,'use_rsi':use_rsi,'eligible':eligible,'score':score,**{k:v for k,v in m.items() if k!='annual'}})
        gd=pd.DataFrame(grid).sort_values(['eligible','score','candidate'],ascending=[False,False,True]); gd.to_csv(out/'train_grid.csv',index=False)
        elig=gd[gd.eligible]
        if elig.empty:
            res={'status':'BTC_BREAKOUT_V3_TRAIN_NO_GO','data':diag,'n_candidates':4,'n_eligible':0,'oos_2026_opened':False}
            (out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2)); return
        sel=elig.iloc[0]; name=str(sel.candidate); L=int(sel.L); use_rsi=bool(sel.use_rsi)
        trains[name].to_csv(out/'selected_train_trades.csv',index=False)
        train_m=metrics(trains[name]); freeze={'candidate':name,'L':L,'use_rsi':use_rsi,'score':float(sel.score),'train':train_m}
        (out/'SELECTED_PRECONFIRM.json').write_text(json.dumps(freeze,indent=2))
        conf=simulate(b,L,use_rsi,'2023-01-01','2024-01-01',v1.COSTS['PRIMARY']); conf.to_csv(out/'confirm_2023_trades.csv',index=False)
        cm=metrics(conf)
        conf_pass=(cm['n']>=40 and cm['mean'] is not None and cm['mean']>=0.05 and cm['pf'] is not None and cm['pf']>=1.10
                   and cm['positive_years']==1 and cm['active_years']==1 and cm['max_dd'] is not None and cm['max_dd']<=10.0)
        if not conf_pass:
            res={'status':'BTC_BREAKOUT_V3_CONFIRM_2023_NO_GO','data':diag,'selected':freeze,'confirm_2023':cm,
                 'confirmation_pass':False,'validation_2024_2025_opened':False,'oos_2026_opened':False}
            (out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2)); return
        vp=simulate(b,L,use_rsi,'2024-01-01','2026-01-01',v1.COSTS['PRIMARY']); vs=simulate(b,L,use_rsi,'2024-01-01','2026-01-01',v1.COSTS['STRESS'])
        vp.to_csv(out/'validation_primary_trades.csv',index=False); vs.to_csv(out/'validation_stress_trades.csv',index=False)
        mp=metrics(vp); ms=metrics(vs)
        val_pass=(mp['n']>=100 and mp['mean'] is not None and mp['mean']>=0.08 and mp['pf'] is not None and mp['pf']>=1.15
                  and mp['positive_years']==2 and mp['active_years']==2 and mp['max_dd'] is not None and mp['max_dd']<=12.0
                  and ms['mean'] is not None and ms['mean']>0 and ms['pf'] is not None and ms['pf']>1.05)
        status='BTC_BREAKOUT_V3_READY_FOR_2026_OOS_FREEZE' if val_pass else 'BTC_BREAKOUT_V3_VALIDATION_NO_GO'
        res={'status':status,'data':diag,'selected':freeze,'confirm_2023':cm,'confirmation_pass':True,
             'validation_primary':mp,'validation_stress':ms,'validation_pass':val_pass,'oos_2026_opened':False}
        (out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2))
    except Exception as e:
        res={'status':'BTC_BREAKOUT_V3_INVALID_ABORT','error':repr(e),'oos_2026_opened':False}
        (out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2)); raise

if __name__=='__main__': main()
