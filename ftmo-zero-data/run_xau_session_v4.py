#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('xauv3base', HERE / 'run_xau_v3.py')
B = importlib.util.module_from_spec(SPEC); sys.modules['xauv3base'] = B; SPEC.loader.exec_module(B)

OUT = Path('ftmo-zero-data/results/xau_session_v4'); OUT.mkdir(parents=True, exist_ok=True)
DEV_YEARS = [2021, 2022, 2023]
VAL_YEAR = 2024
SIG_START = 8*60+20
SIG_END = 11*60+30
FORCE_EXIT = 15*60+55
BOOT_SEED = 260822


@dataclass(frozen=True)
class Candidate:
    family: str
    threshold_atr: float
    rr: float
    @property
    def name(self): return f'{self.family}_THR{int(self.threshold_atr*100):02d}_RR{self.rr:.1f}'


def candidates():
    return [Candidate(f,t,r) for f in ('ASIA_SWEEP','LONDON_SWEEP','ASIA_BREAK','LONDON_BREAK')
            for t in (0.0,0.10) for r in (1.5,2.0)]


def build_m5(raw):
    z=raw.set_index('time').sort_index()
    x=z.resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),count=('close','count')).dropna(subset=['open','high','low','close'])
    x=x[x['count']>=4].copy(); pc=x.close.shift(1)
    tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1)
    x['atr14']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); x=x.dropna(subset=['atr14']).reset_index()
    x['ny_date']=x.time.dt.date; x['minute']=x.time.dt.hour*60+x.time.dt.minute
    # Asia D = D-1 18:00 through D 01:59. Adding six hours maps both parts to D.
    af=x[(x.minute>=18*60)|(x.minute<2*60)].copy(); af['range_date']=(af.time+pd.Timedelta(hours=6)).dt.date
    asia=af.groupby('range_date').agg(asia_high=('high','max'),asia_low=('low','min'),asia_count=('close','count'))
    asia.loc[asia.asia_count<72,['asia_high','asia_low']]=np.nan
    lf=x[(x.minute>=2*60)&(x.minute<SIG_START)].copy()
    london=lf.groupby('ny_date').agg(london_high=('high','max'),london_low=('low','min'),london_count=('close','count'))
    london.loc[london.london_count<57,['london_high','london_low']]=np.nan
    x['asia_high']=x.ny_date.map(asia.asia_high.to_dict()); x['asia_low']=x.ny_date.map(asia.asia_low.to_dict())
    x['london_high']=x.ny_date.map(london.london_high.to_dict()); x['london_low']=x.ny_date.map(london.london_low.to_dict())
    return x


def prepare_days(df):
    cols=['time','minute','open','high','low','close','atr14','asia_high','asia_low','london_high','london_low','ny_date']
    out=[]
    for date,g in df.groupby('ny_date',sort=True):
        g=g[(g.minute>=SIG_START)&(g.minute<=FORCE_EXIT)][cols].sort_values('time').reset_index(drop=True)
        if len(g)>=2:
            d={c:g[c].to_numpy() for c in cols}; d['date']=date; out.append(d)
    return out


def levels(d,c):
    if c.family.startswith('ASIA'): return float(d['asia_high'][0]),float(d['asia_low'][0])
    return float(d['london_high'][0]),float(d['london_low'][0])


def simulate(days,c,stress=False):
    spread,slip=B.scenario(stress); rows=[]
    for d in days:
        rh,rl=levels(d,c)
        if not np.isfinite(rh) or not np.isfinite(rl): continue
        minute=d['minute']; op=d['open']; hi=d['high']; lo=d['low']; cl=d['close']; atr=d['atr14']; times=d['time']; L=len(minute)
        i=0; n=0; last_entry=None; used=set(); break_used=False
        while i<L-1 and n<3:
            if minute[i]>SIG_END: break
            a=float(atr[i]); thr=c.threshold_atr*a; side=None
            if c.family.endswith('SWEEP'):
                if 'long' not in used and lo[i]<=rl-thr and cl[i]>rl: side='long'
                elif 'short' not in used and hi[i]>=rh+thr and cl[i]<rh: side='short'
            else:
                if break_used: break
                if cl[i]>rh+thr: side='long'
                elif cl[i]<rl-thr: side='short'
            if side is None: i+=1; continue
            eidx=i+1
            if minute[eidx]>SIG_END+5: break
            if last_entry is not None and (pd.Timestamp(times[eidx])-pd.Timestamp(last_entry)).total_seconds()<1800:
                i+=1; continue
            bid=float(op[eidx])
            if c.family.endswith('SWEEP'):
                stop_bid=float(lo[i])-0.10*a if side=='long' else float(hi[i])+0.10*a
            else:
                stop_bid=bid-a if side=='long' else bid+a
            if side=='long':
                entry=B.long_entry_net(bid,spread,slip); stop_net=B.long_exit_net(stop_bid,slip); risk=entry-stop_net
                if risk<=0: i+=1; continue
                target_bid=(entry+c.rr*risk+slip)/(1-B.COMMISSION_RATE)
                si=np.flatnonzero(lo[eidx:]<=stop_bid); ti=np.flatnonzero(hi[eidx:]>=target_bid)
            else:
                entry=B.short_entry_net(bid,slip); stop_net=B.short_exit_net_from_bid(stop_bid,spread,slip); risk=stop_net-entry
                if risk<=0: i+=1; continue
                desired=entry-c.rr*risk; target_ask=(desired-slip)/(1+B.COMMISSION_RATE); target_bid=target_ask-spread
                si=np.flatnonzero(hi[eidx:]>=stop_bid); ti=np.flatnonzero((lo[eidx:]+spread)<=(target_bid+spread))
            js=int(si[0]+eidx) if len(si) else None; jt=int(ti[0]+eidx) if len(ti) else None
            if js is not None and (jt is None or js<=jt):
                exi=js; ex=B.long_exit_net(stop_bid,slip) if side=='long' else B.short_exit_net_from_bid(stop_bid,spread,slip); reason='stop'
            elif jt is not None:
                exi=jt; ex=B.long_exit_net(target_bid,slip) if side=='long' else B.short_exit_net_from_bid(target_bid,spread,slip); reason='target'
            else:
                exi=L-1; ex=B.long_exit_net(float(cl[exi]),slip) if side=='long' else B.short_exit_net_from_bid(float(cl[exi]),spread,slip); reason='time'
            pnl=ex-entry if side=='long' else entry-ex
            rows.append({'date':str(d['date']),'entry_time':str(times[eidx]),'exit_time':str(times[exi]),'family':c.family,'candidate':c.name,'direction':side,'range_high':rh,'range_low':rl,'r':float(pnl/risk),'exit_reason':reason,'stress':stress})
            last_entry=times[eidx]; n+=1
            if c.family.endswith('SWEEP'): used.add(side)
            else: break_used=True
            i=max(exi+1,i+1)
    return pd.DataFrame(rows)


def pf(a):
    p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e9 if p>0 else None)

def stats(t):
    if t.empty:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None}
    a=t.r.to_numpy(float); eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.,eq])[:-1]; dd=np.maximum(peaks-eq,0)
    return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0))}

def by_year(t):
    if t.empty:return {}
    z=t.copy();z['year']=pd.to_datetime(z.date).dt.year;return {str(k):stats(g) for k,g in z.groupby('year')}

def month_rate(t):
    if t.empty:return 0.,0
    z=t.copy();z['month']=pd.to_datetime(z.date).dt.to_period('M').astype(str); s=z.groupby('month').r.sum(); return float((s>0).mean()),int(len(s))

def halves(t):
    if t.empty:return {'H1':0.,'H2':0.}
    dt=pd.to_datetime(t.date);return {'H1':float(t.loc[dt.dt.month<=6,'r'].sum()),'H2':float(t.loc[dt.dt.month>=7,'r'].sum())}

def boot(t,nrep=5000,block=20):
    a=t.r.to_numpy(float)
    if len(a)<block:return None
    rng=np.random.default_rng(BOOT_SEED); means=np.empty(nrep); maxstart=len(a)-block; need=math.ceil(len(a)/block)
    for k in range(nrep):
        starts=rng.integers(0,maxstart+1,size=need); sample=np.concatenate([a[s:s+block] for s in starts])[:len(a)]; means[k]=sample.mean()
    return float(np.quantile(means,.05))

def sessions(df): return int(df[df.minute==SIG_START].ny_date.nunique())

def dev_gate(p,s,ns):
    a=stats(p); b=stats(s); ys=by_year(p); mr,nm=month_rate(p); bt=boot(p); means=[v['mean'] for v in ys.values() if v['mean'] is not None]; worst=min(means) if means else None; py=sum(v['sum']>0 for v in ys.values()); rps=a['sum']/ns if ns else 0.; srps=b['sum']/ns if ns else 0.
    g={'n_ge_250':a['n']>=250,'mean_ge_0_15':a['mean'] is not None and a['mean']>=.15,'pf_ge_1_30':a['pf'] is not None and a['pf']>=1.30,'rps_ge_0_30':rps>=.30,'maxdd_le_12':a['max_dd'] is not None and a['max_dd']<=12,'positive_years_ge_2':py>=2,'worst_year_mean_ge_0':worst is not None and worst>=0,'months_ge_58':mr>=.58,'stress_mean_gt_0':b['mean'] is not None and b['mean']>0,'stress_pf_ge_1_15':b['pf'] is not None and b['pf']>=1.15,'stress_rps_ge_0_12':srps>=.12,'bootstrap_p05_ge_0':bt is not None and bt>=0}
    return all(g.values()),{'primary':a,'stress':b,'yearly':ys,'sessions':ns,'r_per_session':rps,'stress_r_per_session':srps,'positive_years':py,'worst_year_mean':worst,'positive_month_rate':mr,'active_months':nm,'bootstrap_p05_mean':bt,'gates':g}

def score(d): return float(2*d['worst_year_mean']+1.5*d['stress_r_per_session']+d['r_per_session']+.5*d['primary']['mean']-.02*d['primary']['max_dd'])
def val_gate(p,s,ns):
    a=stats(p); b=stats(s); mr,nm=month_rate(p); h=halves(p); bt=boot(p); rps=a['sum']/ns if ns else 0.; srps=b['sum']/ns if ns else 0.
    g={'n_ge_70':a['n']>=70,'mean_ge_0_15':a['mean'] is not None and a['mean']>=.15,'pf_ge_1_30':a['pf'] is not None and a['pf']>=1.30,'rps_ge_0_35':rps>=.35,'maxdd_le_10':a['max_dd'] is not None and a['max_dd']<=10,'stress_mean_gt_0':b['mean'] is not None and b['mean']>0,'stress_pf_ge_1_15':b['pf'] is not None and b['pf']>=1.15,'stress_rps_ge_0_15':srps>=.15,'h1_positive':h['H1']>0,'h2_positive':h['H2']>0,'months_ge_58':mr>=.58,'bootstrap_p05_ge_0':bt is not None and bt>=0}
    return all(g.values()),{'primary':a,'stress':b,'sessions':ns,'r_per_session':rps,'stress_r_per_session':srps,'half_sums':h,'positive_month_rate':mr,'active_months':nm,'bootstrap_p05_mean':bt,'gates':g}

def qa(x,y):
    z=x[x.time.dt.year==y]; return {'year':y,'m5_rows':int(len(z)),'first':str(z.time.min()),'last':str(z.time.max()),'duplicates':int(z.duplicated('time').sum()),'morning_sessions':sessions(z),'price_min':float(z.low.min()) if len(z) else None,'price_max':float(z.high.max()) if len(z) else None}


def main():
    # DEV first. No 2024 strategy result is computed unless a DEV candidate passes.
    raw_dev=pd.concat([B.load_year(y) for y in DEV_YEARS],ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    mdev=build_m5(raw_dev); ns=sessions(mdev); days=prepare_days(mdev); results={}; cmap={c.name:c for c in candidates()}
    for c in candidates():
        p=simulate(days,c,False); s=simulate(days,c,True); ok,d=dev_gate(p,s,ns); d.update({'candidate':asdict(c),'name':c.name,'eligible':ok,'robustness_score':score(d) if ok else None}); results[c.name]=d
    selected={}
    for fam in ('ASIA_SWEEP','LONDON_SWEEP','ASIA_BREAK','LONDON_BREAK'):
        es=[d for d in results.values() if d['candidate']['family']==fam and d['eligible']]; selected[fam]=max(es,key=lambda z:z['robustness_score'])['name'] if es else None
    validation={fam:{'status':'DEV_FAMILY_REJECTED_NO_VALIDATION','selected':None} for fam in selected}; qa_data={str(y):qa(mdev,y) for y in DEV_YEARS}; val_open=False; traces=[]
    if any(selected.values()):
        raw_val=B.load_year(VAL_YEAR); raw_all=pd.concat([raw_dev.tail(15000),raw_val],ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True); mall=build_m5(raw_all); mval=mall[mall.time.dt.year==VAL_YEAR].copy(); val_open=True; qa_data[str(VAL_YEAR)]=qa(mval,VAL_YEAR); vns=sessions(mval); vdays=prepare_days(mval)
        for fam,name in selected.items():
            if not name: continue
            c=cmap[name]; p=simulate(vdays,c,False); s=simulate(vdays,c,True); ok,d=val_gate(p,s,vns); d['selected']=name; d['status']='VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS' if ok else 'VALIDATION_NO_GO'; validation[fam]=d
            if not p.empty: z=p.copy();z['stage']='VAL_PRIMARY';traces.append(z)
            if not s.empty: z=s.copy();z['stage']='VAL_STRESS';traces.append(z)
    out={'status':'XAU_SESSION_V4_COMPLETE_2025_UNOPENED','hard_constraint':'ZERO_PAID_EXTERNAL_DATA_REQUIRED_LIVE','partitions':{'DEV':'2021-2023','VALIDATION':'2024_GATED','OOS_2025':'SEALED_NOT_DOWNLOADED'},'validation_2024_economic_opened':val_open,'oos_2025_opened':False,'candidate_count':len(candidates()),'data_qa':qa_data,'dev_sessions':ns,'dev_results':results,'selected_by_family':selected,'validation':validation}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str))
    pd.DataFrame([{'name':d['name'],'family':d['candidate']['family'],'eligible':d['eligible'],'n':d['primary']['n'],'mean':d['primary']['mean'],'pf':d['primary']['pf'],'r_per_session':d['r_per_session'],'max_dd':d['primary']['max_dd'],'stress_mean':d['stress']['mean'],'stress_pf':d['stress']['pf'],'stress_r_per_session':d['stress_r_per_session'],'worst_year_mean':d['worst_year_mean'],'month_rate':d['positive_month_rate'],'bootstrap_p05':d['bootstrap_p05_mean'],'score':d['robustness_score']} for d in results.values()]).to_csv(OUT/'DEV_SCREEN.csv',index=False)
    if traces: pd.concat(traces,ignore_index=True).to_csv(OUT/'VALIDATION_TRADES.csv',index=False)
    print(json.dumps({'status':out['status'],'selected':selected,'validation':validation},indent=2,default=str))
if __name__=='__main__': main()
