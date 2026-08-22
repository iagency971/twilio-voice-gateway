#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path('ftmo-zero-data/results/xau_rsi_v5')
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://raw.githubusercontent.com/tiumbj/M1_XAUUSD/main/DAT_MT_XAUUSD_M1_{}.csv'
FIXED_EST = 'Etc/GMT+5'
NY = 'America/New_York'
DEV_YEARS = [2021, 2022, 2023]
WARMUP_YEAR = 2020
VAL_YEAR = 2024
RSI_PERIOD = 14
SL_DOLLARS = 10.0
COMMISSION_RATE = 0.000007
BLOCKED_UTC_HOURS = {1,2,3,4,5,21,22,23}
COOLDOWN_MIN = 40
MAX_LOSSES_UTC_DAY = 2
BOOT_SEED = 260822

@dataclass(frozen=True)
class Candidate:
    short_level: float
    long_level: float
    trend_filter: bool
    @property
    def name(self) -> str:
        return f'RSI{int(self.short_level)}_{int(self.long_level)}_' + ('TREND' if self.trend_filter else 'BI')

def candidates():
    return [Candidate(63.0,37.0,True), Candidate(63.0,37.0,False),
            Candidate(70.0,30.0,True), Candidate(70.0,30.0,False)]

def load_year(year: int) -> pd.DataFrame:
    if year >= 2025:
        raise RuntimeError('V5 outcome-blind guard: 2025+ access forbidden')
    names=['date_s','time_s','open','high','low','close','volume']
    d=pd.read_csv(BASE.format(year),names=names,header=None)
    naive=pd.to_datetime(d.date_s.astype(str)+' '+d.time_s.astype(str),format='%Y.%m.%d %H:%M',errors='coerce')
    fixed=pd.DatetimeIndex(naive).tz_localize(FIXED_EST)
    d['time']=fixed.tz_convert(NY)
    for c in ('open','high','low','close','volume'): d[c]=pd.to_numeric(d[c],errors='coerce')
    return d.dropna(subset=['time','open','high','low','close']).sort_values('time').drop_duplicates('time',keep='last')[['time','open','high','low','close','volume']].reset_index(drop=True)

def wilder_rsi(s: pd.Series, period: int=14) -> pd.Series:
    delta=s.diff(); gain=delta.clip(lower=0.0); loss=-delta.clip(upper=0.0)
    ag=gain.ewm(alpha=1/period,min_periods=period,adjust=False).mean()
    al=loss.ewm(alpha=1/period,min_periods=period,adjust=False).mean()
    rs=ag/al
    return 100-(100/(1+rs))

def build_m5(raw: pd.DataFrame) -> pd.DataFrame:
    z=raw.set_index('time').sort_index()
    x=z.resample('5min',label='left',closed='left').agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),count=('close','count')).dropna(subset=['open','high','low','close'])
    x=x[x['count']>=4].copy(); x['rsi']=wilder_rsi(x.close,RSI_PERIOD); x['prev_rsi']=x.rsi.shift(1)
    x=x.reset_index(); x['session_key']=(x.time-pd.Timedelta(hours=17)).dt.date
    sess=x.groupby('session_key',sort=True).agg(sess_close=('close','last'),bars=('close','count'))
    sess['ema50']=sess.sess_close.ewm(span=50,adjust=False).mean()
    sess['prior_close']=sess.sess_close.shift(1); sess['prior_ema50']=sess.ema50.shift(1)
    sess['bias']=np.where(sess.prior_close>sess.prior_ema50,'long','short')
    sess.loc[sess.prior_ema50.isna(),'bias']=None
    x['bias']=x.session_key.map(sess.bias.to_dict())
    utc=x.time.dt.tz_convert('UTC'); x['utc_time']=utc; x['utc_date']=utc.dt.date; x['utc_hour']=utc.dt.hour; x['utc_minute']=utc.dt.hour*60+utc.dt.minute; x['utc_weekday']=utc.dt.weekday
    x['ny_minute']=x.time.dt.hour*60+x.time.dt.minute
    return x.dropna(subset=['rsi','prev_rsi']).reset_index(drop=True)

def session_deadline(session_key) -> pd.Timestamp:
    return pd.Timestamp(session_key).tz_localize(NY)+pd.Timedelta(days=1,hours=16,minutes=55)

def scenario(stress: bool): return (0.50,0.05) if stress else (0.30,0.0)
def comm(p: float): return max(float(p),0.0)*COMMISSION_RATE

def long_entry(bid,spread,slip):
    raw=float(bid)+spread+slip; return raw, raw+comm(raw)
def long_exit(bid,slip):
    raw=float(bid)-slip; return raw-comm(raw)
def short_entry(bid,slip):
    raw=float(bid)-slip; return raw, raw-comm(raw)
def short_exit_from_bid(bid,spread,slip):
    raw=float(bid)+spread+slip; return raw+comm(raw)

def broad_fomc_block(r) -> bool:
    return int(r.utc_weekday)==2 and 17*60 <= int(r.utc_minute) <= 20*60+30

def entry_time_allowed(r) -> bool:
    if int(r.utc_hour) in BLOCKED_UTC_HOURS: return False
    if broad_fomc_block(r): return False
    if int(r.utc_weekday)==4 and int(r.utc_hour)>=19: return False
    return True

def available_sessions(m5: pd.DataFrame, years: list[int]) -> int:
    z=m5[m5.time.dt.year.isin(years)].copy()
    counts=z.groupby('session_key').size()
    return int((counts>=200).sum())

def simulate(m5: pd.DataFrame, c: Candidate, stress: bool=False) -> pd.DataFrame:
    spread,slip=scenario(stress); rows=[]; i=0; L=len(m5); cooldown_until=None; current_utc_day=None; losses_today=0
    while i<L-1:
        r=m5.iloc[i]; sig_time=pd.Timestamp(r.time); utc_time=pd.Timestamp(r.utc_time); uday=r.utc_date
        if uday!=current_utc_day:
            current_utc_day=uday; losses_today=0
        side=None
        if entry_time_allowed(r) and losses_today<MAX_LOSSES_UTC_DAY and (cooldown_until is None or utc_time>=cooldown_until):
            if r.prev_rsi<=c.short_level<r.rsi: side='short'
            elif r.prev_rsi>=c.long_level>r.rsi: side='long'
            if side and c.trend_filter and r.bias!=side: side=None
        if side is None:
            i+=1; continue
        eidx=i+1; e=m5.iloc[eidx]; deadline=session_deadline(e.session_key)
        if pd.Timestamp(e.time)>=deadline:
            i+=1; continue
        if side=='long':
            raw_entry,entry_net=long_entry(e.open,spread,slip)
            stop_bid=raw_entry-SL_DOLLARS
            stop_net=long_exit(stop_bid,slip)
            risk=entry_net-stop_net
        else:
            raw_entry,entry_net=short_entry(e.open,slip)
            stop_ask=raw_entry+SL_DOLLARS
            stop_bid=stop_ask-spread
            stop_net=short_exit_from_bid(stop_bid,spread,slip)
            risk=stop_net-entry_net
        if not np.isfinite(risk) or risk<=0:
            i+=1; continue
        exidx=None; exit_net=None; reason=None; exit_time=None; j=eidx
        while j<L:
            b=m5.iloc[j]; bt=pd.Timestamp(b.time)
            if bt>=deadline:
                exidx=j
                exit_net=long_exit(b.open,slip) if side=='long' else short_exit_from_bid(b.open,spread,slip)
                reason='rollover_flat'; exit_time=bt; break
            if side=='long':
                if float(b.open)<=stop_bid:
                    exidx=j; exit_net=long_exit(float(b.open),slip); reason='stop_gap'; exit_time=bt; break
                if float(b.low)<=stop_bid:
                    exidx=j; exit_net=long_exit(stop_bid,slip); reason='stop'; exit_time=bt; break
                rsi_exit=bool(float(b.rsi)>=c.short_level)
            else:
                ask_open=float(b.open)+spread
                if ask_open>=stop_ask:
                    exidx=j; exit_net=short_exit_from_bid(float(b.open),spread,slip); reason='stop_gap'; exit_time=bt; break
                if float(b.high)+spread>=stop_ask:
                    exidx=j; exit_net=short_exit_from_bid(stop_bid,spread,slip); reason='stop'; exit_time=bt; break
                rsi_exit=bool(float(b.rsi)<=c.long_level)
            if rsi_exit:
                nx=j+1
                if nx>=L:
                    exidx=j; exit_net=long_exit(b.close,slip) if side=='long' else short_exit_from_bid(b.close,spread,slip); reason='end'; exit_time=bt; break
                nb=m5.iloc[nx]; nbt=pd.Timestamp(nb.time)
                if nbt>=deadline:
                    exidx=nx; exit_net=long_exit(nb.open,slip) if side=='long' else short_exit_from_bid(nb.open,spread,slip); reason='rollover_flat'; exit_time=nbt; break
                if side=='long' and float(nb.open)<=stop_bid:
                    exidx=nx; exit_net=long_exit(float(nb.open),slip); reason='stop_gap'; exit_time=nbt; break
                if side=='short' and float(nb.open)+spread>=stop_ask:
                    exidx=nx; exit_net=short_exit_from_bid(float(nb.open),spread,slip); reason='stop_gap'; exit_time=nbt; break
                exidx=nx; exit_net=long_exit(nb.open,slip) if side=='long' else short_exit_from_bid(nb.open,spread,slip); reason='rsi'; exit_time=nbt; break
            j+=1
        if exidx is None: break
        pnl=(exit_net-entry_net) if side=='long' else (entry_net-exit_net)
        rv=float(pnl/risk); exit_utc=pd.Timestamp(exit_time).tz_convert('UTC'); exit_uday=exit_utc.date()
        if exit_uday!=current_utc_day:
            current_utc_day=exit_uday; losses_today=0
        if pnl<0:
            losses_today+=1; cooldown_until=exit_utc+pd.Timedelta(minutes=COOLDOWN_MIN)
        rows.append({'date':str(pd.Timestamp(e.time).date()),'entry_time':str(e.time),'exit_time':str(exit_time),'candidate':c.name,'direction':side,'r':rv,'pnl_price_net':float(pnl),'risk_price_net':float(risk),'entry_rsi':float(r.rsi),'bias':r.bias,'exit_reason':reason,'stress':stress})
        i=max(int(exidx),i+1)
    return pd.DataFrame(rows)

def pf(a):
    p=a[a>0].sum(); n=-a[a<0].sum(); return float(p/n) if n>0 else (1e9 if p>0 else None)
def stats(t):
    if t.empty:return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'avg_hold_min':None}
    a=t.r.to_numpy(float);eq=np.cumsum(a);pk=np.maximum.accumulate(np.r_[0.,eq])[:-1];dd=np.maximum(pk-eq,0)
    hold=(pd.to_datetime(t.exit_time,utc=True)-pd.to_datetime(t.entry_time,utc=True)).dt.total_seconds()/60
    return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0)),'avg_hold_min':float(hold.mean())}
def by_year(t):
    if t.empty:return {}
    z=t.copy();z['year']=pd.to_datetime(z.date).dt.year;return {str(k):stats(g) for k,g in z.groupby('year')}
def month_rate(t):
    if t.empty:return 0.,0
    z=t.copy();z['month']=pd.to_datetime(z.date).dt.to_period('M').astype(str);s=z.groupby('month').r.sum();return float((s>0).mean()),int(len(s))
def halves(t):
    if t.empty:return {'H1':0.,'H2':0.}
    d=pd.to_datetime(t.date);return {'H1':float(t.loc[d.dt.month<=6,'r'].sum()),'H2':float(t.loc[d.dt.month>=7,'r'].sum())}
def boot(t,nrep=5000,block=20):
    a=t.r.to_numpy(float)
    if len(a)<block:return None
    rng=np.random.default_rng(BOOT_SEED);means=np.empty(nrep);mx=len(a)-block;need=math.ceil(len(a)/block)
    for k in range(nrep):
        starts=rng.integers(0,mx+1,size=need);sample=np.concatenate([a[s:s+block] for s in starts])[:len(a)];means[k]=sample.mean()
    return float(np.quantile(means,.05))
def dev_gate(p,s,ns):
    a=stats(p);b=stats(s);ys=by_year(p);mr,nm=month_rate(p);bt=boot(p);means=[v['mean'] for v in ys.values() if v['mean'] is not None];worst=min(means) if means else None;py=sum(v['sum']>0 for v in ys.values());tpd=a['n']/ns if ns else 0.;rps=a['sum']/ns if ns else 0.;srps=b['sum']/ns if ns else 0.
    g={'n_ge_500':a['n']>=500,'trades_per_session_ge_0_65':tpd>=.65,'mean_ge_0_12':a['mean'] is not None and a['mean']>=.12,'pf_ge_1_25':a['pf'] is not None and a['pf']>=1.25,'rps_ge_0_30':rps>=.30,'maxdd_le_12':a['max_dd'] is not None and a['max_dd']<=12,'positive_years_ge_2':py>=2,'worst_year_mean_ge_0':worst is not None and worst>=0,'months_ge_58':mr>=.58,'stress_mean_ge_0_03':b['mean'] is not None and b['mean']>=.03,'stress_pf_ge_1_10':b['pf'] is not None and b['pf']>=1.10,'stress_rps_ge_0_12':srps>=.12,'bootstrap_p05_ge_0':bt is not None and bt>=0}
    return all(g.values()),{'primary':a,'stress':b,'yearly':ys,'sessions':ns,'trades_per_session':tpd,'r_per_session':rps,'stress_r_per_session':srps,'positive_years':py,'worst_year_mean':worst,'positive_month_rate':mr,'active_months':nm,'bootstrap_p05_mean':bt,'gates':g}
def score(d):return float(2*d['worst_year_mean']+1.5*d['stress_r_per_session']+d['r_per_session']+.5*d['primary']['mean']-.02*d['primary']['max_dd'])
def val_gate(p,s,ns):
    a=stats(p);b=stats(s);mr,nm=month_rate(p);h=halves(p);bt=boot(p);tpd=a['n']/ns if ns else 0.;rps=a['sum']/ns if ns else 0.;srps=b['sum']/ns if ns else 0.
    g={'n_ge_150':a['n']>=150,'trades_per_session_ge_0_65':tpd>=.65,'mean_ge_0_12':a['mean'] is not None and a['mean']>=.12,'pf_ge_1_25':a['pf'] is not None and a['pf']>=1.25,'rps_ge_0_35':rps>=.35,'maxdd_le_10':a['max_dd'] is not None and a['max_dd']<=10,'stress_mean_ge_0_03':b['mean'] is not None and b['mean']>=.03,'stress_pf_ge_1_10':b['pf'] is not None and b['pf']>=1.10,'stress_rps_ge_0_15':srps>=.15,'h1_positive':h['H1']>0,'h2_positive':h['H2']>0,'months_ge_58':mr>=.58,'bootstrap_p05_ge_0':bt is not None and bt>=0}
    return all(g.values()),{'primary':a,'stress':b,'sessions':ns,'trades_per_session':tpd,'r_per_session':rps,'stress_r_per_session':srps,'half_sums':h,'positive_month_rate':mr,'active_months':nm,'bootstrap_p05_mean':bt,'gates':g}

def main():
    raw=pd.concat([load_year(WARMUP_YEAR)]+[load_year(y) for y in DEV_YEARS],ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    m5=build_m5(raw);dev=m5[m5.time.dt.year.isin(DEV_YEARS)].copy().reset_index(drop=True);ns=available_sessions(m5,DEV_YEARS);res={}
    for c in candidates():
        p=simulate(dev,c,False);s=simulate(dev,c,True);ok,d=dev_gate(p,s,ns);d.update({'candidate':asdict(c),'name':c.name,'eligible':ok,'robustness_score':score(d) if ok else None});res[c.name]=d
    elig=[d for d in res.values() if d['eligible']];selected=max(elig,key=lambda z:z['robustness_score'])['name'] if elig else None
    validation={'status':'DEV_NO_GO_2024_NOT_OPENED','selected':None};val_open=False;traces=[]
    if selected:
        raw24=load_year(VAL_YEAR);allraw=pd.concat([raw.tail(120000),raw24],ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True);m24=build_m5(allraw);val=m24[m24.time.dt.year==VAL_YEAR].copy().reset_index(drop=True);vns=available_sessions(m24,[VAL_YEAR]);c={x.name:x for x in candidates()}[selected];p=simulate(val,c,False);s=simulate(val,c,True);ok,d=val_gate(p,s,vns);d['selected']=selected;d['status']='VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS' if ok else 'VALIDATION_NO_GO';validation=d;val_open=True
        if not p.empty:z=p.copy();z['stage']='VAL_PRIMARY';traces.append(z)
        if not s.empty:z=s.copy();z['stage']='VAL_STRESS';traces.append(z)
    out={'status':'XAU_RSI_V5_COMPLETE_2025_UNOPENED','external_hypothesis':{'repo':'olivertwigg/XAU-RSI-Reversal-50-EMA-Bot','commit':'f74adfada07a1538f2bf9f87eb9158dcd7d86a47'},'hard_constraint':'ZERO_PAID_EXTERNAL_DATA_REQUIRED_LIVE','partitions':{'WARMUP':'2020','DEV':'2021-2023','VALIDATION':'2024_GATED','OOS_2025':'SEALED_NOT_DOWNLOADED'},'validation_2024_economic_opened':val_open,'oos_2025_opened':False,'dev_sessions':ns,'candidate_count':4,'dev_results':res,'selected':selected,'validation':validation}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str));pd.DataFrame([{'name':d['name'],'eligible':d['eligible'],'n':d['primary']['n'],'tps':d['trades_per_session'],'mean':d['primary']['mean'],'pf':d['primary']['pf'],'rps':d['r_per_session'],'max_dd':d['primary']['max_dd'],'avg_hold_min':d['primary']['avg_hold_min'],'stress_mean':d['stress']['mean'],'stress_pf':d['stress']['pf'],'stress_rps':d['stress_r_per_session'],'worst_year_mean':d['worst_year_mean'],'month_rate':d['positive_month_rate'],'bootstrap_p05':d['bootstrap_p05_mean'],'score':d['robustness_score']} for d in res.values()]).to_csv(OUT/'DEV_SCREEN.csv',index=False)
    if traces:pd.concat(traces,ignore_index=True).to_csv(OUT/'VALIDATION_TRADES.csv',index=False)
    print(json.dumps({'status':out['status'],'selected':selected,'validation':validation},indent=2,default=str))
if __name__=='__main__':main()
