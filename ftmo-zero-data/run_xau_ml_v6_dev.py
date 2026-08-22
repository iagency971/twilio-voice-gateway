#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

OUT=Path('ftmo-zero-data/results/xau_ml_v6_dev'); OUT.mkdir(parents=True,exist_ok=True)
BASE='https://raw.githubusercontent.com/tiumbj/M1_XAUUSD/main/DAT_MT_XAUUSD_M1_{}.csv'
FIXED_EST='Etc/GMT+5'; NY='America/New_York'
YEARS=[2020,2021,2022,2023]
COMMISSION_RATE=0.000007
SIGNAL_START=7*60; SIGNAL_END=15*60+45; FORCE_EXIT=16*60+55
BOOT_SEED=260822
FEATURES=['ret1_atr','ret3_atr','ret6_atr','ret12_atr','rsi14','c_ema20_atr','c_ema50_atr','ema20_50_atr','ema20_slope3_atr','body_atr','range_atr','z20','loc20','atr_pct','rstd12','tod_sin','tod_cos','dow_sin','dow_cos']

@dataclass(frozen=True)
class Candidate:
    threshold: float
    mode: str
    @property
    def name(self): return f'ML{int(self.threshold*100)}_{self.mode}'

def candidates(): return [Candidate(.55,'BI'),Candidate(.60,'BI'),Candidate(.55,'LONG'),Candidate(.60,'LONG')]

def load_year(y):
    if y>=2024: raise RuntimeError('V6 DEV guard: 2024+ access forbidden')
    names=['date_s','time_s','open','high','low','close','volume']
    d=pd.read_csv(BASE.format(y),names=names,header=None)
    naive=pd.to_datetime(d.date_s.astype(str)+' '+d.time_s.astype(str),format='%Y.%m.%d %H:%M',errors='coerce')
    d['time']=pd.DatetimeIndex(naive).tz_localize(FIXED_EST).tz_convert(NY)
    for c in ('open','high','low','close','volume'): d[c]=pd.to_numeric(d[c],errors='coerce')
    return d.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time',keep='last')[['time','open','high','low','close']].reset_index(drop=True)

def rsi(s,p=14):
    d=s.diff();g=d.clip(lower=0);l=-d.clip(upper=0);ag=g.ewm(alpha=1/p,min_periods=p,adjust=False).mean();al=l.ewm(alpha=1/p,min_periods=p,adjust=False).mean();rs=ag/al;return 100-(100/(1+rs))

def build(raw):
    z=raw.set_index('time').sort_index();x=z.resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),count=('close','count')).dropna(subset=['open','high','low','close']);x=x[x['count']>=4].copy()
    pc=x.close.shift(1);tr=pd.concat([(x.high-x.low),(x.high-pc).abs(),(x.low-pc).abs()],axis=1).max(axis=1);x['atr14']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean();x['ema20']=x.close.ewm(span=20,adjust=False).mean();x['ema50']=x.close.ewm(span=50,adjust=False).mean();x['rsi14']=rsi(x.close)/100.0
    for k in (1,3,6,12): x[f'ret{k}_atr']=(x.close-x.close.shift(k))/x.atr14
    x['c_ema20_atr']=(x.close-x.ema20)/x.atr14;x['c_ema50_atr']=(x.close-x.ema50)/x.atr14;x['ema20_50_atr']=(x.ema20-x.ema50)/x.atr14;x['ema20_slope3_atr']=(x.ema20-x.ema20.shift(3))/x.atr14;x['body_atr']=(x.close-x.open)/x.atr14;x['range_atr']=(x.high-x.low)/x.atr14
    m20=x.close.rolling(20).mean();sd20=x.close.rolling(20).std();x['z20']=(x.close-m20)/sd20;hh=x.high.rolling(20).max();ll=x.low.rolling(20).min();x['loc20']=(x.close-ll)/(hh-ll);x['atr_pct']=x.atr14/x.close;x['rstd12']=x.close.pct_change().rolling(12).std()
    x=x.reset_index();x['session_key']=(x.time-pd.Timedelta(hours=17)).dt.date;x['ny_minute']=x.time.dt.hour*60+x.time.dt.minute;x['dow']=x.time.dt.weekday;frac=(x.ny_minute/(24*60))*2*np.pi;x['tod_sin']=np.sin(frac);x['tod_cos']=np.cos(frac);dw=x.dow/7*2*np.pi;x['dow_sin']=np.sin(dw);x['dow_cos']=np.cos(dw);x['row_id']=np.arange(len(x))
    # labels: signal at i, reference entry at next bar open, barriers over i+1..i+12.
    entry=x.open.shift(-1);atr=x.atr14;lt=entry+2.25*atr;ls=entry-1.50*atr;st=entry-2.25*atr;ss=entry+1.50*atr
    inf=np.full(len(x),99,dtype=int);flt=inf.copy();fls=inf.copy();fst=inf.copy();fss=inf.copy()
    for k in range(1,13):
        h=x.high.shift(-k).to_numpy();l=x.low.shift(-k).to_numpy();
        m=(flt==99)&(h>=lt.to_numpy());flt[m]=k;m=(fls==99)&(l<=ls.to_numpy());fls[m]=k;m=(fst==99)&(l<=st.to_numpy());fst[m]=k;m=(fss==99)&(h>=ss.to_numpy());fss[m]=k
    x['y_long']=((flt<fls)&(flt<=12)).astype(int);x['y_short']=((fst<fss)&(fst<=12)).astype(int)
    t12=x.time.shift(-12);same60=(t12-x.time==pd.Timedelta(minutes=60));same_session=(x.session_key==x.session_key.shift(-12));window=(x.ny_minute>=SIGNAL_START)&(x.ny_minute<=SIGNAL_END)
    x['eligible']=same60&same_session&window&x[FEATURES].notna().all(axis=1)&entry.notna()&atr.notna()
    return x

def model(): return HistGradientBoostingClassifier(max_iter=150,learning_rate=.05,max_leaf_nodes=15,min_samples_leaf=100,l2_regularization=1.0,random_state=BOOT_SEED)
def prob1(m,X):
    p=m.predict_proba(X);cl=list(m.classes_);return p[:,cl.index(1)] if 1 in cl else np.zeros(len(X))

def fold_predictions(x,test_year):
    train=x[(x.time.dt.year<test_year)&(x.time.dt.year>=2020)&x.eligible].copy();test=x[(x.time.dt.year==test_year)&x.eligible].copy();
    ml=model();ms=model();ml.fit(train[FEATURES],train.y_long);ms.fit(train[FEATURES],train.y_short);test['p_long']=prob1(ml,test[FEATURES]);test['p_short']=prob1(ms,test[FEATURES]);return test[['row_id','time','p_long','p_short']]

def scenario(stress): return (.50,.05) if stress else (.30,0.0)
def cm(p): return max(float(p),0.0)*COMMISSION_RATE
def le(b,s,sl): raw=float(b)+s+sl;return raw+cm(raw)
def lx(b,sl): raw=float(b)-sl;return raw-cm(raw)
def se(b,sl): raw=float(b)-sl;return raw-cm(raw)
def sx(b,s,sl): raw=float(b)+s+sl;return raw+cm(raw)
def deadline(sk): return pd.Timestamp(sk).tz_localize(NY)+pd.Timedelta(days=1,hours=16,minutes=55)

def simulate_year(x,preds,c,stress=False):
    d=x[x.time.dt.year==pd.Timestamp(preds.time.iloc[0]).year].copy().reset_index(drop=True);mp=preds.set_index('row_id')[['p_long','p_short']].to_dict('index');spread,slip=scenario(stress);rows=[];i=0;counts={};last_entry={}
    while i<len(d)-1:
        r=d.iloc[i];pr=mp.get(int(r.row_id));
        if not pr: i+=1;continue
        pl=float(pr['p_long']);ps=float(pr['p_short']);side=None
        if c.mode=='LONG':
            if pl>=c.threshold: side='long'
        else:
            if max(pl,ps)>=c.threshold: side='long' if pl>=ps else 'short'
        if side is None:i+=1;continue
        sk=r.session_key
        if counts.get(sk,0)>=3:i+=1;continue
        eidx=i+1;e=d.iloc[eidx];et=pd.Timestamp(e.time);dl=deadline(e.session_key)
        if et>=dl:i+=1;continue
        if sk in last_entry and (et-last_entry[sk]).total_seconds()<1800:i+=1;continue
        a=float(r.atr14);bid=float(e.open)
        if not np.isfinite(a) or a<=0:i+=1;continue
        if side=='long':
            entry=le(bid,spread,slip);stop_bid=bid-1.5*a;stopnet=lx(stop_bid,slip);risk=entry-stopnet
            if risk<=0:i+=1;continue
            target_net=entry+1.5*risk;target_bid=(target_net+slip)/(1-COMMISSION_RATE)
        else:
            entry=se(bid,slip);stop_bid=bid+1.5*a;stopnet=sx(stop_bid,spread,slip);risk=stopnet-entry
            if risk<=0:i+=1;continue
            target_net=entry-1.5*risk;target_ask=(target_net-slip)/(1+COMMISSION_RATE);target_bid=target_ask-spread
        exi=None;ex=None;reason=None;horizon=et+pd.Timedelta(minutes=60);j=eidx
        while j<len(d):
            b=d.iloc[j];bt=pd.Timestamp(b.time)
            if bt>=dl or bt>=horizon:
                exi=j;ex=lx(b.open,slip) if side=='long' else sx(b.open,spread,slip);reason='time';break
            if side=='long':
                if float(b.open)<=stop_bid:exi=j;ex=lx(b.open,slip);reason='stop_gap';break
                hs=float(b.low)<=stop_bid;ht=float(b.high)>=target_bid
                if hs:exi=j;ex=lx(stop_bid,slip);reason='stop';break
                if ht:exi=j;ex=lx(target_bid,slip);reason='target';break
            else:
                if float(b.open)+spread>=stop_bid+spread:exi=j;ex=sx(b.open,spread,slip);reason='stop_gap';break
                hs=float(b.high)>=stop_bid;ht=float(b.low)+spread<=target_bid+spread
                if hs:exi=j;ex=sx(stop_bid,spread,slip);reason='stop';break
                if ht:exi=j;ex=sx(target_bid,spread,slip);reason='target';break
            j+=1
        if exi is None:break
        pnl=ex-entry if side=='long' else entry-ex;rv=float(pnl/risk);rows.append({'date':str(et.date()),'entry_time':str(et),'exit_time':str(d.iloc[exi].time),'candidate':c.name,'direction':side,'p_long':pl,'p_short':ps,'r':rv,'exit_reason':reason,'stress':stress});counts[sk]=counts.get(sk,0)+1;last_entry[sk]=et;i=max(exi,i+1)
    return pd.DataFrame(rows)

def sessions(x,year):
    z=x[(x.time.dt.year==year)&(x.ny_minute>=SIGNAL_START)&(x.ny_minute<=SIGNAL_END)];cnt=z.groupby('session_key').size();return int((cnt>=80).sum())
def pf(a):p=a[a>0].sum();n=-a[a<0].sum();return float(p/n) if n>0 else (1e9 if p>0 else None)
def stats(t):
    if t.empty:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None}
    a=t.r.to_numpy(float);eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq])[:-1];dd=np.maximum(pk-eq,0);return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0))}
def yearly(t):
    z=t.copy();z['year']=pd.to_datetime(z.date).dt.year;return {str(k):stats(g) for k,g in z.groupby('year')}
def month_rate(t):
    z=t.copy();z['month']=pd.to_datetime(z.date).dt.to_period('M').astype(str);s=z.groupby('month').r.sum();return float((s>0).mean()),int(len(s))
def rb10(t):
    a=np.sort(t.r.to_numpy(float));n=max(1,int(math.ceil(len(a)*.10)));keep=a[:-n] if n<len(a) else np.array([]);return float(keep.mean()) if len(keep) else None
def boot(t,nrep=5000,block=20):
    a=t.r.to_numpy(float)
    if len(a)<block:return None
    rng=np.random.default_rng(BOOT_SEED);means=np.empty(nrep);mx=len(a)-block;need=math.ceil(len(a)/block)
    for k in range(nrep):st=rng.integers(0,mx+1,size=need);s=np.concatenate([a[q:q+block] for q in st])[:len(a)];means[k]=s.mean()
    return float(np.quantile(means,.05))
def gate(p,s,ns):
    a=stats(p);b=stats(s);ys=yearly(p);mr,nm=month_rate(p);r=rb10(p);bt=boot(p);tps=a['n']/ns if ns else 0.;rps=a['sum']/ns if ns else 0.;srps=b['sum']/ns if ns else 0.;means=[v['mean'] for v in ys.values()];worst=min(means) if means else None;allyears=all(v['sum']>0 for v in ys.values()) and len(ys)==3
    g={'n_ge_500':a['n']>=500,'tps_ge_0_65':tps>=.65,'mean_ge_0_15':a['mean'] is not None and a['mean']>=.15,'pf_ge_1_30':a['pf'] is not None and a['pf']>=1.30,'rps_ge_0_35':rps>=.35,'maxdd_le_12':a['max_dd'] is not None and a['max_dd']<=12,'all_years_positive':allyears,'worst_year_mean_ge_0_05':worst is not None and worst>=.05,'months_ge_60':mr>=.60,'remove_best10_ge_0':r is not None and r>=0,'stress_mean_ge_0_05':b['mean'] is not None and b['mean']>=.05,'stress_pf_ge_1_15':b['pf'] is not None and b['pf']>=1.15,'stress_rps_ge_0_15':srps>=.15,'bootstrap_p05_ge_0':bt is not None and bt>=0}
    return all(g.values()),{'primary':a,'stress':b,'yearly':ys,'sessions':ns,'trades_per_session':tps,'r_per_session':rps,'stress_r_per_session':srps,'worst_year_mean':worst,'positive_month_rate':mr,'active_months':nm,'remove_best10_mean':r,'bootstrap_p05_mean':bt,'gates':g}
def score(d):return float(2*d['worst_year_mean']+1.5*d['stress_r_per_session']+d['r_per_session']+d['remove_best10_mean']-.02*d['primary']['max_dd'])

def main():
    raw=pd.concat([load_year(y) for y in YEARS],ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True);x=build(raw);preds={};fold_diag={}
    for y in (2021,2022,2023):
        pr=fold_predictions(x,y);preds[y]=pr;tr=x[(x.time.dt.year<y)&(x.time.dt.year>=2020)&x.eligible];te=x[(x.time.dt.year==y)&x.eligible];fold_diag[str(y)]={'train_n':int(len(tr)),'test_n':int(len(te)),'train_long_success_rate':float(tr.y_long.mean()),'train_short_success_rate':float(tr.y_short.mean()),'test_long_success_rate':float(te.y_long.mean()),'test_short_success_rate':float(te.y_short.mean()),'sessions':sessions(x,y)}
    ns=sum(sessions(x,y) for y in (2021,2022,2023));results={}
    for c in candidates():
        pp=[];ss=[]
        for y in (2021,2022,2023):pp.append(simulate_year(x,preds[y],c,False));ss.append(simulate_year(x,preds[y],c,True))
        p=pd.concat(pp,ignore_index=True) if pp else pd.DataFrame();s=pd.concat(ss,ignore_index=True) if ss else pd.DataFrame();ok,d=gate(p,s,ns);d.update({'candidate':asdict(c),'name':c.name,'eligible':ok,'robustness_score':score(d) if ok else None});results[c.name]=d
    elig=[d for d in results.values() if d['eligible']];selected=max(elig,key=lambda z:z['robustness_score'])['name'] if elig else None
    out={'status':'XAU_ML_V6_DEV_WALKFORWARD_COMPLETE','hard_constraint':'ZERO_PAID_EXTERNAL_DATA_REQUIRED_LIVE','partitions':{'TRAIN_CONTEXT':'2020','DEV_WALK_FORWARD':'2021-2023','VALIDATION_2024':'NOT_OPENED','OOS_2025':'SEALED_NOT_OPENED'},'validation_2024_opened':False,'oos_2025_opened':False,'feature_names':FEATURES,'fold_diagnostics':fold_diag,'dev_sessions':ns,'candidate_count':4,'dev_results':results,'selected':selected}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str));pd.DataFrame([{'name':d['name'],'eligible':d['eligible'],'n':d['primary']['n'],'tps':d['trades_per_session'],'mean':d['primary']['mean'],'pf':d['primary']['pf'],'rps':d['r_per_session'],'max_dd':d['primary']['max_dd'],'rb10':d['remove_best10_mean'],'stress_mean':d['stress']['mean'],'stress_pf':d['stress']['pf'],'stress_rps':d['stress_r_per_session'],'worst_year_mean':d['worst_year_mean'],'month_rate':d['positive_month_rate'],'bootstrap_p05':d['bootstrap_p05_mean'],'score':d['robustness_score']} for d in results.values()]).to_csv(OUT/'DEV_SCREEN.csv',index=False);print(json.dumps({'status':out['status'],'selected':selected},indent=2))
if __name__=='__main__':main()
