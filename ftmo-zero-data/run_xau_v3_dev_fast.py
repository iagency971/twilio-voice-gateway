#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
import importlib.util

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('xauv3', HERE / 'run_xau_v3.py')
M = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
OUT = Path('ftmo-zero-data/results/xau_v3_fast'); OUT.mkdir(parents=True, exist_ok=True)


def prepare_days(df: pd.DataFrame):
    cols = ['time','minute','open','high','low','close','atr14','ema20','prev_close','prev_ema20',
            'h1_ema20','h1_ema50','h1_ema50_lag3','prev_session_high','prev_session_low','ny_date']
    out=[]
    for date,g in df.groupby('ny_date',sort=True):
        g=g[(g.minute>=M.SIGNAL_START)&(g.minute<=M.FORCE_EXIT)][cols].sort_values('time').reset_index(drop=True)
        if len(g)<2: continue
        d={c:g[c].to_numpy() for c in cols}
        d['date']=date
        out.append(d)
    return out


def simulate(days,c,stress=False):
    spread,slip=M.scenario(stress); rows=[]
    for d in days:
        minute=d['minute']; op=d['open']; hi=d['high']; lo=d['low']; cl=d['close']; atr=d['atr14']
        em20=d['ema20']; pcl=d['prev_close']; pem20=d['prev_ema20']; h20=d['h1_ema20']; h50=d['h1_ema50']; h503=d['h1_ema50_lag3']; psh=d['prev_session_high']; psl=d['prev_session_low']; times=d['time']
        i=0; n=0; last_entry=None; used=set(); L=len(minute)
        while i<L-1 and n<M.MAX_TRADES_DAY:
            if minute[i]>M.SIGNAL_END: break
            side=None
            if c.family.startswith('PB'):
                long_ok=(h20[i]>h50[i] and h50[i]>h503[i] and pcl[i]<=pem20[i] and cl[i]>em20[i])
                if long_ok: side='long'
                elif c.family=='PB_BI' and h20[i]<h50[i] and h50[i]<h503[i] and pcl[i]>=pem20[i] and cl[i]<em20[i]: side='short'
            else:
                if np.isfinite(psl[i]) and np.isfinite(psh[i]):
                    pen=float(c.penetration_atr)*float(atr[i])
                    if 'long' not in used and lo[i]<=psl[i]-pen and cl[i]>psl[i]: side='long'
                    elif c.family=='SWEEP_BI' and 'short' not in used and hi[i]>=psh[i]+pen and cl[i]<psh[i]: side='short'
            if side is None: i+=1; continue
            eidx=i+1
            if minute[eidx]>M.SIGNAL_END+5: break
            if last_entry is not None and (pd.Timestamp(times[eidx])-pd.Timestamp(last_entry)).total_seconds()<M.COOLDOWN_MIN*60:
                i+=1; continue
            a=float(atr[i]); bid=float(op[eidx])
            if not np.isfinite(a) or a<=0: i+=1; continue
            if c.family.startswith('PB'):
                stop_bid=bid-float(c.stop_atr)*a if side=='long' else bid+float(c.stop_atr)*a
            else:
                stop_bid=float(lo[i])-0.10*a if side=='long' else float(hi[i])+0.10*a
            if (side=='long' and bid<=stop_bid) or (side=='short' and bid>=stop_bid): i+=1; continue
            if side=='long':
                entry=M.long_entry_net(bid,spread,slip); stop_net=M.long_exit_net(stop_bid,slip); risk=entry-stop_net
                if risk<=0: i+=1; continue
                target_bid=(entry+c.rr*risk+slip)/(1.0-M.COMMISSION_RATE)
                sidx=np.flatnonzero(lo[eidx:]<=stop_bid); tidx=np.flatnonzero(hi[eidx:]>=target_bid)
            else:
                entry=M.short_entry_net(bid,slip); stop_net=M.short_exit_net_from_bid(stop_bid,spread,slip); risk=stop_net-entry
                if risk<=0: i+=1; continue
                desired=entry-c.rr*risk; target_ask=(desired-slip)/(1.0+M.COMMISSION_RATE); target_bid=target_ask-spread
                sidx=np.flatnonzero((hi[eidx:]+spread)>=(stop_bid+spread)); tidx=np.flatnonzero((lo[eidx:]+spread)<=(target_bid+spread))
            js=int(sidx[0]+eidx) if len(sidx) else None; jt=int(tidx[0]+eidx) if len(tidx) else None
            if js is not None and (jt is None or js<=jt):
                exi=js; ex=M.long_exit_net(stop_bid,slip) if side=='long' else M.short_exit_net_from_bid(stop_bid,spread,slip); reason='stop'
            elif jt is not None:
                exi=jt; ex=M.long_exit_net(target_bid,slip) if side=='long' else M.short_exit_net_from_bid(target_bid,spread,slip); reason='target'
            else:
                exi=L-1; ex=M.long_exit_net(float(cl[exi]),slip) if side=='long' else M.short_exit_net_from_bid(float(cl[exi]),spread,slip); reason='time'
            pnl=ex-entry if side=='long' else entry-ex
            rows.append({'date':str(d['date']),'entry_time':str(times[eidx]),'exit_time':str(times[exi]),'family':c.family,'candidate':c.name,'direction':side,'r':float(pnl/risk),'stress':stress,'exit_reason':reason})
            last_entry=times[eidx]
            if c.family.startswith('SWEEP'): used.add(side)
            n+=1; i=max(exi+1,i+1)
    return pd.DataFrame(rows)


def main():
    # DEV only. No 2024 and no 2025 request exists in this script.
    raw=pd.concat([M.load_year(y) for y in M.DEV_YEARS],ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    m5=M.build_features(raw); dev_sessions=sum(M.qa_year(m5,y)['morning_sessions'] for y in M.DEV_YEARS); days=prepare_days(m5)
    results={}; selected={}
    for c in M.candidates():
        p=simulate(days,c,False); s=simulate(days,c,True); ok,det=M.dev_gate(p,s,dev_sessions); det.update({'candidate':asdict(c),'name':c.name,'eligible':ok,'robustness_score':M.robustness_score(det) if ok else None}); results[c.name]=det
    for fam in ('PB_LONG','PB_BI','SWEEP_LONG','SWEEP_BI'):
        es=[d for d in results.values() if d['candidate']['family']==fam and d['eligible']]
        selected[fam]=max(es,key=lambda z:z['robustness_score'])['name'] if es else None
    out={'status':'XAU_V3_FAST_DEV_COMPLETE','partition':'DEV_2021_2023_ONLY','validation_2024_opened':False,'oos_2025_opened':False,'dev_sessions':dev_sessions,'selected_by_family':selected,'dev_results':results}
    (OUT/'RESULT.json').write_text(json.dumps(out,indent=2,allow_nan=False,default=str))
    pd.DataFrame([{'name':d['name'],'family':d['candidate']['family'],'eligible':d['eligible'],'n':d['primary']['n'],'mean':d['primary']['mean'],'pf':d['primary']['pf'],'r_per_session':d['r_per_session'],'max_dd':d['primary']['max_dd'],'stress_mean':d['stress']['mean'],'stress_pf':d['stress']['pf'],'stress_r_per_session':d['stress_r_per_session'],'worst_year_mean':d['worst_year_mean'],'month_rate':d['positive_month_rate'],'bootstrap_p05':d['bootstrap_p05_mean'],'score':d['robustness_score']} for d in results.values()]).to_csv(OUT/'DEV_SCREEN.csv',index=False)
    print(json.dumps({'status':out['status'],'selected':selected},indent=2))
if __name__=='__main__': main()
