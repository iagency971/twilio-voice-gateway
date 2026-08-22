#!/usr/bin/env python3
from __future__ import annotations
import json, math
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path('ftmo-zero-data/results/ustec_trend_v2'); OUT.mkdir(parents=True,exist_ok=True)
BASE='https://raw.githubusercontent.com/CodyOutcast/Academic-Paper-Data-Source/main/OHLC-USTEC-M1-{}.csv'
DEV_YEARS=[2021,2022,2023]; VAL_YEAR=2024
TRADE_START=16*60+30; SIGNAL_END=22*60+30; FORCE_EXIT=22*60+55
BOOT_SEED=260822

@dataclass(frozen=True)
class Cfg:
    strength: float
    stop_atr: float
    rr: float
    @property
    def name(self): return f'TREND_S{int(self.strength*100):02d}_SL{self.stop_atr:.1f}_RR{self.rr:.1f}'

def configs(): return [Cfg(s,sl,rr) for s in (0.0,0.10) for sl in (1.0,1.5) for rr in (1.5,2.0)]

def load_year(y):
    if y>=2025: raise RuntimeError('V2 guard: 2025+ forbidden')
    d=pd.read_csv(BASE.format(y),sep=';'); d.columns=[str(c).strip().lower() for c in d.columns]
    d['time']=pd.to_datetime(d.time,format='%Y.%m.%d %H:%M:%S',errors='coerce')
    for c in ('open','high','low','close','volume','spread'): d[c]=pd.to_numeric(d[c],errors='coerce')
    return d.dropna(subset=['time','open','high','low','close','spread']).sort_values('time').drop_duplicates('time').reset_index(drop=True)

def to_m5(d):
    x=d.set_index('time').resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),volume=('volume','sum'),spread=('spread','last'),m1_count=('close','count')).dropna(subset=['open','high','low','close','spread']).reset_index()
    x=x[x.m1_count>=4].copy(); x['ema20']=x.close.ewm(span=20,adjust=False).mean(); x['ema50']=x.close.ewm(span=50,adjust=False).mean()
    prev=x.close.shift(1); tr=pd.concat([(x.high-x.low),(x.high-prev).abs(),(x.low-prev).abs()],axis=1).max(axis=1)
    x['atr14']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); x['ema50_lag3']=x.ema50.shift(3); x['prev_close']=x.close.shift(1); x['prev_ema20']=x.ema20.shift(1)
    x['date']=x.time.dt.date; x['minute']=x.time.dt.hour*60+x.time.dt.minute
    return x.dropna(subset=['atr14','ema50_lag3','prev_close','prev_ema20']).reset_index(drop=True)

def sp(v,stress):
    v=max(float(v),0.0); return max(v*1.5,v+1.0) if stress else v

def signal(row,c):
    atr=float(row.atr14)
    if atr<=0:return None
    ls=(row.ema20-row.ema50)/atr; ss=(row.ema50-row.ema20)/atr
    if row.ema20>row.ema50 and row.ema50>row.ema50_lag3 and ls>=c.strength and row.prev_close<=row.prev_ema20 and row.close>row.ema20:return 'long'
    if row.ema20<row.ema50 and row.ema50<row.ema50_lag3 and ss>=c.strength and row.prev_close>=row.prev_ema20 and row.close<row.ema20:return 'short'
    return None

def run_day(day,c,stress=False):
    day=day.sort_values('time').reset_index(drop=True); rows=[]; i=0; last_entry=None
    while i<len(day)-1 and len(rows)<3:
        r=day.loc[i]
        if r.minute<TRADE_START or r.minute>SIGNAL_END:i+=1;continue
        side=signal(r,c)
        if side is None:i+=1;continue
        eidx=i+1; e=day.loc[eidx]
        if e.minute>FORCE_EXIT:break
        if last_entry is not None and (e.time-last_entry).total_seconds()<1800:i+=1;continue
        atr=float(r.atr14); spr=sp(e.spread,stress); slip=.5 if stress else 0.0; bid=float(e.open)
        if side=='long':
            entry=bid+spr+slip; stop_bid=bid-c.stop_atr*atr; risk=entry-stop_bid; target_bid=entry+c.rr*risk
        else:
            entry=bid-slip; stop_bid_struct=bid+c.stop_atr*atr; stop_ask=stop_bid_struct+spr+slip; risk=stop_ask-entry; target_ask=entry-c.rr*risk
        if risk<=0:i+=1;continue
        exit_i=None; exit_px=None; reason=None
        for j in range(eidx,len(day)):
            b=day.loc[j]
            if b.minute>FORCE_EXIT:break
            bs=sp(b.spread,stress)
            if side=='long':
                ht=float(b.high)>=target_bid; hs=float(b.low)<=stop_bid
                if ht and hs:ht=False
                if hs:exit_i=j;exit_px=stop_bid-slip;reason='stop';break
                if ht:exit_i=j;exit_px=target_bid-slip;reason='target';break
            else:
                ah=float(b.high)+bs; al=float(b.low)+bs; ht=al<=target_ask; hs=ah>=stop_ask
                if ht and hs:ht=False
                if hs:exit_i=j;exit_px=stop_ask+slip;reason='stop';break
                if ht:exit_i=j;exit_px=target_ask+slip;reason='target';break
        if exit_i is None:
            elig=day[(day.index>=eidx)&(day.minute<=FORCE_EXIT)]
            if elig.empty:break
            b=elig.iloc[-1]; exit_i=int(b.name); bs=sp(b.spread,stress); exit_px=float(b.close)-slip if side=='long' else float(b.close)+bs+slip; reason='time'
        pnl=(exit_px-entry) if side=='long' else (entry-exit_px)
        rows.append({'date':str(e.date),'entry_time':str(e.time),'exit_time':str(day.loc[exit_i].time),'direction':side,'candidate':c.name,'entry':entry,'exit':exit_px,'risk_points':risk,'atr':atr,'spread_entry':spr,'r':float(pnl/risk),'exit_reason':reason,'stress':stress})
        last_entry=e.time; i=max(exit_i+1,i+1)
    return rows

def run(df,c,stress=False):
    rows=[]
    for _,d in df.groupby('date',sort=True):rows.extend(run_day(d,c,stress))
    return pd.DataFrame(rows)

def pf(a):
    p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e9 if p>0 else None)

def stats(t):
    if t.empty:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None}
    a=t.r.to_numpy(float); eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(peak-eq,0)
    return {'n':len(a),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0))}

def by_year(t):
    if t.empty:return {}
    z=t.copy();z['year']=pd.to_datetime(z.date).dt.year
    return {str(k):stats(g) for k,g in z.groupby('year')}

def month_rate(t):
    if t.empty:return 0.,0
    z=t.copy();z['month']=pd.to_datetime(z.date).dt.to_period('M').astype(str); s=z.groupby('month').r.sum();return float((s>0).mean()),len(s)

def halves(t):
    d=pd.to_datetime(t.date) if not t.empty else pd.Series(dtype='datetime64[ns]')
    return {'H1':float(t.loc[d.dt.month<=6,'r'].sum()) if len(d) else 0.,'H2':float(t.loc[d.dt.month>=7,'r'].sum()) if len(d) else 0.}

def bootstrap_p05(t,nrep=5000,block=20):
    a=t.r.to_numpy(float)
    if len(a)<block:return None
    rng=np.random.default_rng(BOOT_SEED); means=np.empty(nrep); maxstart=len(a)-block; need=math.ceil(len(a)/block)
    for k in range(nrep):
        starts=rng.integers(0,maxstart+1,size=need); sample=np.concatenate([a[s:s+block] for s in starts])[:len(a)];means[k]=sample.mean()
    return float(np.quantile(means,.05))

def qa(m5,y):
    return {'year':y,'m5_rows':len(m5),'first':str(m5.time.min()),'last':str(m5.time.max()),'duplicates':int(m5.duplicated('time').sum()),'open_sessions':int(m5[m5.minute==TRADE_START].date.nunique()),'spread_mean':float(m5.spread.mean()),'spread_p95':float(m5.spread.quantile(.95))}

def dev_gate(p,s,sessions):
    st=stats(p); ss=stats(s); ys=by_year(p); mr,nm=month_rate(p); b=bootstrap_p05(p); means=[v['mean'] for v in ys.values() if v['mean'] is not None]; worst=min(means) if means else None; py=sum(v['sum']>0 for v in ys.values()); tpd=st['n']/sessions if sessions else 0
    g={'n_ge_900':st['n']>=900,'trades_per_day_ge_1_5':tpd>=1.5,'mean_ge_0_10':st['mean'] is not None and st['mean']>=.10,'pf_ge_1_25':st['pf'] is not None and st['pf']>=1.25,'maxdd_le_15':st['max_dd'] is not None and st['max_dd']<=15,'positive_years_ge_2':py>=2,'worst_year_mean_ge_0':worst is not None and worst>=0,'positive_month_rate_ge_55':mr>=.55,'stress_mean_gt_0':ss['mean'] is not None and ss['mean']>0,'stress_pf_ge_1_10':ss['pf'] is not None and ss['pf']>=1.10,'bootstrap_p05_ge_0':b is not None and b>=0}
    return all(g.values()),{'primary':st,'stress':ss,'yearly':ys,'trades_per_day':tpd,'positive_month_rate':mr,'active_months':nm,'worst_year_mean':worst,'positive_years':py,'bootstrap_p05_mean':b,'gates':g}

def score(d):
    p=d['primary'];return 2*d['worst_year_mean']+d['stress']['mean']+p['mean']-.01*p['max_dd']+.02*math.log(p['n'])

def val_gate(p,s,sessions):
    st=stats(p);ss=stats(s);mr,nm=month_rate(p);h=halves(p);b=bootstrap_p05(p);tpd=st['n']/sessions if sessions else 0
    g={'n_ge_300':st['n']>=300,'trades_per_day_ge_1_5':tpd>=1.5,'mean_ge_0_12':st['mean'] is not None and st['mean']>=.12,'pf_ge_1_25':st['pf'] is not None and st['pf']>=1.25,'maxdd_le_12':st['max_dd'] is not None and st['max_dd']<=12,'stress_mean_ge_0_05':ss['mean'] is not None and ss['mean']>=.05,'stress_pf_ge_1_15':ss['pf'] is not None and ss['pf']>=1.15,'h1_positive':h['H1']>0,'h2_positive':h['H2']>0,'positive_month_rate_ge_58':mr>=.58,'bootstrap_p05_ge_0':b is not None and b>=0}
    return all(g.values()),{'primary':st,'stress':ss,'trades_per_day':tpd,'positive_month_rate':mr,'active_months':nm,'half_sums':h,'bootstrap_p05_mean':b,'gates':g}

def main():
    m5={y:to_m5(load_year(y)) for y in DEV_YEARS+[VAL_YEAR]}; q={str(y):qa(m5[y],y) for y in m5}; dev=pd.concat([m5[y] for y in DEV_YEARS],ignore_index=True).sort_values('time').reset_index(drop=True); val=m5[VAL_YEAR]
    dev_sessions=sum(q[str(y)]['open_sessions'] for y in DEV_YEARS); val_sessions=q[str(VAL_YEAR)]['open_sessions']; dr={}
    for c in configs():
        p=run(dev,c,False);s=run(dev,c,True);ok,d=dev_gate(p,s,dev_sessions);d.update({'name':c.name,'config':asdict(c),'eligible':ok,'score':score(d) if ok else None});dr[c.name]=d
    elig=[d for d in dr.values() if d['eligible']]; selected=max(elig,key=lambda z:z['score'])['name'] if elig else None; validation={'status':'DEV_NO_GO_2024_NOT_OPENED','selected':None}; traces=[]
    if selected:
        c={x.name:x for x in configs()}[selected];p=run(val,c,False);s=run(val,c,True);ok,d=val_gate(p,s,val_sessions);d['selected']=selected;d['status']='VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS' if ok else 'VALIDATION_NO_GO';validation=d
        if not p.empty:z=p.copy();z['stage']='VAL_PRIMARY';traces.append(z)
        if not s.empty:z=s.copy();z['stage']='VAL_STRESS';traces.append(z)
    res={'status':'USTEC_TREND_V2_COMPLETE_2025_UNOPENED','hard_constraint':'ZERO_PAID_EXTERNAL_DATA_REQUIRED_LIVE','partitions':{'DEV':'2021-2023','VALIDATION':'2024','OOS_2025':'SEALED_NOT_DOWNLOADED'},'data_qa':q,'dev_sessions':dev_sessions,'candidate_count':len(configs()),'dev_results':dr,'selected':selected,'validation':validation,'oos_2025_opened':False}
    (OUT/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False,default=str))
    pd.DataFrame([{'name':d['name'],'eligible':d['eligible'],'n':d['primary']['n'],'tpd':d['trades_per_day'],'mean':d['primary']['mean'],'pf':d['primary']['pf'],'max_dd':d['primary']['max_dd'],'stress_mean':d['stress']['mean'],'stress_pf':d['stress']['pf'],'worst_year_mean':d['worst_year_mean'],'month_rate':d['positive_month_rate'],'bootstrap_p05':d['bootstrap_p05_mean'],'score':d['score']} for d in dr.values()]).to_csv(OUT/'DEV_SCREEN.csv',index=False)
    if traces:pd.concat(traces,ignore_index=True).to_csv(OUT/'VALIDATION_TRADES.csv',index=False)
    print(json.dumps({'status':res['status'],'selected':selected,'validation':validation},indent=2,default=str))
if __name__=='__main__':main()
