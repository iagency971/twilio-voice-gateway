#!/usr/bin/env python3
from __future__ import annotations

import io, json, math
from pathlib import Path
import requests
import numpy as np
import pandas as pd

URL = 'https://raw.githubusercontent.com/lvrusu/QQQ_price_data/main/QQQ5m_Ext_J_23_to_Mar_20a_2026.csv'
START = pd.Timestamp('2023-04-25')
END_MAX = pd.Timestamp('2026-03-20')

SCENARIOS = {
    'PRIMARY': {'slip_bp': 1.0, 'commission_side': 0.005},
    'STRESS': {'slip_bp': 2.0, 'commission_side': 0.01},
}


def metrics(x: pd.DataFrame):
    if x.empty:
        return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None}
    r=x.net_R.astype(float).to_numpy()
    pos=r[r>0].sum(); neg=-r[r<0].sum()
    pf=float(pos/neg) if neg>0 else (float('inf') if pos>0 else None)
    eq=np.cumsum(r); peaks=np.maximum.accumulate(np.r_[0.0,eq])[:-1]; dd=peaks-eq
    maxdd=float(max(0.0, dd.max(initial=0.0)))
    streak=cur=0
    for v in r:
        if v<0: cur+=1; streak=max(streak,cur)
        else: cur=0
    return {'n':int(len(r)),'mean':float(np.mean(r)),'sum':float(np.sum(r)),'pf':pf,
            'win_rate':float(np.mean(r>0)),'max_dd':maxdd,'losing_streak':int(streak)}


def load_data(out: Path):
    resp=requests.get(URL,timeout=120)
    resp.raise_for_status()
    raw=resp.content
    if len(raw)<10000: raise RuntimeError(f'data download unexpectedly small: {len(raw)} bytes')
    df=pd.read_csv(io.BytesIO(raw))
    orig=list(df.columns)
    cols={c.lower().strip():c for c in df.columns}
    dt_col=cols.get('ds') or cols.get('datetime') or cols.get('timestamp') or cols.get('date')
    if not dt_col: raise RuntimeError(f'no datetime column in {orig}')
    ren={dt_col:'dt'}
    for want in ['open','high','low','close']:
        src=cols.get(want)
        if not src: raise RuntimeError(f'missing {want} in {orig}')
        ren[src]=want
    df=df.rename(columns=ren)
    df['dt']=pd.to_datetime(df['dt'],errors='coerce')
    for c in ['open','high','low','close']: df[c]=pd.to_numeric(df[c],errors='coerce')
    df=df.dropna(subset=['dt','open','high','low','close']).copy()
    if 'unique_id' in df.columns: df=df[df['unique_id'].astype(str).str.upper().eq('QQQ')]
    df=df.sort_values('dt').drop_duplicates('dt',keep='last')
    df=df[(df.dt.dt.normalize()>=START)&(df.dt.dt.normalize()<=END_MAX)].copy()
    if df.empty: raise RuntimeError('no post-publication rows after filtering')
    diag={'source_url':URL,'download_bytes':len(raw),'original_columns':orig,'rows_retained':int(len(df)),
          'dt_min':str(df.dt.min()),'dt_max':str(df.dt.max()),'duplicate_dt_after_dedupe':int(df.dt.duplicated().sum())}
    (out/'data_diagnostics.json').write_text(json.dumps(diag,indent=2))
    return df,diag


def simulate_day(day: pd.DataFrame, side: int, sc: dict):
    b0=day[day.dt.dt.strftime('%H:%M').eq('09:30')]
    b1=day[day.dt.dt.strftime('%H:%M').eq('09:35')]
    eod=day[day.dt.dt.strftime('%H:%M').eq('15:55')]
    if len(b0)!=1 or len(b1)!=1 or len(eod)!=1: return None
    b0=b0.iloc[0]; b1=b1.iloc[0]
    slip=sc['slip_bp']/10000.0
    if side==1:
        entry=float(b1.open)*(1+slip); stop=float(b0.low); risk=entry-stop
        if risk<=0: return None
        target=entry+10*risk
    else:
        entry=float(b1.open)*(1-slip); stop=float(b0.high); risk=stop-entry
        if risk<=0: return None
        target=entry-10*risk
    bars=day[(day.dt>=b1['dt'])&(day.dt.dt.strftime('%H:%M')<='15:55')].copy()
    exit_px=None; reason=None; exit_dt=None
    for _,b in bars.iterrows():
        o,h,l,c=map(float,[b.open,b.high,b.low,b.close])
        if side==1:
            if o<=stop:
                exit_px=o*(1-slip); reason='SL_GAP'; exit_dt=b['dt']; break
            if o>=target:
                exit_px=target*(1-slip); reason='TP_GAP_CAPPED'; exit_dt=b['dt']; break
            hit_sl=l<=stop; hit_tp=h>=target
            if hit_sl:
                exit_px=stop*(1-slip); reason='SL' if not hit_tp else 'SL_AMBIG'; exit_dt=b['dt']; break
            if hit_tp:
                exit_px=target*(1-slip); reason='TP'; exit_dt=b['dt']; break
        else:
            if o>=stop:
                exit_px=o*(1+slip); reason='SL_GAP'; exit_dt=b['dt']; break
            if o<=target:
                exit_px=target*(1+slip); reason='TP_GAP_CAPPED'; exit_dt=b['dt']; break
            hit_sl=h>=stop; hit_tp=l<=target
            if hit_sl:
                exit_px=stop*(1+slip); reason='SL' if not hit_tp else 'SL_AMBIG'; exit_dt=b['dt']; break
            if hit_tp:
                exit_px=target*(1+slip); reason='TP'; exit_dt=b['dt']; break
    if exit_px is None:
        b=eod.iloc[0]; exit_dt=b['dt']; reason='TIME'
        exit_px=float(b.close)*(1-slip if side==1 else 1+slip)
    gross_R=side*(exit_px-entry)/risk
    commission_R=(2*sc['commission_side'])/risk
    return {'entry_time':str(b1['dt']),'exit_time':str(exit_dt),'side':'LONG' if side==1 else 'SHORT',
            'entry':entry,'stop':stop,'target':target,'risk_price':risk,'exit':exit_px,'exit_reason':reason,
            'gross_R':gross_R,'commission_R':commission_R,'net_R':gross_R-commission_R}


def main():
    out=Path('qqq-propf/results/postpub_v1'); out.mkdir(parents=True,exist_ok=True)
    try:
        df,diag=load_data(out)
    except Exception as e:
        res={'status':'QQQ_ORB_POSTPUBLICATION_V1_INVALID_DATA_ABORT','error':repr(e)}
        (out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2)); return
    rows=[]; incomplete=[]; doji=0; invalid=0
    for date,g in df.groupby(df.dt.dt.normalize(),sort=True):
        b0=g[g.dt.dt.strftime('%H:%M').eq('09:30')]
        b1=g[g.dt.dt.strftime('%H:%M').eq('09:35')]
        eod=g[g.dt.dt.strftime('%H:%M').eq('15:55')]
        if len(b0)!=1 or len(b1)!=1 or len(eod)!=1:
            incomplete.append(str(date.date())); continue
        first=b0.iloc[0]
        if first.close>first.open: side=1
        elif first.close<first.open: side=-1
        else: doji+=1; continue
        for name,sc in SCENARIOS.items():
            r=simulate_day(g,side,sc)
            if r is None: invalid+=1; continue
            r.update({'date':str(date.date()),'scenario':name})
            rows.append(r)
    tr=pd.DataFrame(rows)
    if tr.empty:
        res={'status':'QQQ_ORB_POSTPUBLICATION_V1_INVALID_DATA_ABORT','error':'no trades'}
        (out/'RESULT.json').write_text(json.dumps(res,indent=2)); print(json.dumps(res,indent=2)); return
    tr.to_csv(out/'trades.csv',index=False)
    summaries={}; annual_rows=[]
    for name in SCENARIOS:
        x=tr[tr.scenario.eq(name)].copy(); x['date_ts']=pd.to_datetime(x.date)
        m=metrics(x)
        A=metrics(x[(x.date_ts>=pd.Timestamp('2023-04-25'))&(x.date_ts<=pd.Timestamp('2024-12-31'))])
        B=metrics(x[x.date_ts>=pd.Timestamp('2025-01-01')])
        k=max(1,math.ceil(0.05*len(x)))
        rem=x.sort_values(['net_R','date'],ascending=[False,True]).iloc[k:]
        conc={'top_n':k,'remaining_mean':float(rem.net_R.mean()) if len(rem) else None}
        summaries[name]={'overall':m,'subperiod_A':A,'subperiod_B':B,'concentration':conc}
        for y,g in x.groupby(x.date_ts.dt.year):
            mm=metrics(g); mm.update({'scenario':name,'year':int(y)}); annual_rows.append(mm)
    pd.DataFrame(annual_rows).to_csv(out/'annual_metrics.csv',index=False)
    p=summaries['PRIMARY']; s=summaries['STRESS']
    pm=p['overall']; sm=s['overall']
    gate={
        'N_ge_400':pm['n']>=400,
        'primary_mean_ge_0_10':pm['mean'] is not None and pm['mean']>=0.10,
        'primary_pf_ge_1_25':pm['pf'] is not None and pm['pf']>=1.25,
        'subperiod_A_positive':p['subperiod_A']['mean'] is not None and p['subperiod_A']['mean']>0 and p['subperiod_A']['pf'] is not None and p['subperiod_A']['pf']>1.05,
        'subperiod_B_positive':p['subperiod_B']['mean'] is not None and p['subperiod_B']['pf'] is not None and p['subperiod_B']['mean']>0 and p['subperiod_B']['pf']>1.05,
        'primary_dd_le_15R':pm['max_dd'] is not None and pm['max_dd']<=15.0,
        'remove_top5_remaining_mean_positive':p['concentration']['remaining_mean'] is not None and p['concentration']['remaining_mean']>0,
        'stress_mean_positive':sm['mean'] is not None and sm['mean']>0,
        'stress_pf_ge_1_10':sm['pf'] is not None and sm['pf']>=1.10,
    }
    passed=all(gate.values())
    status='QQQ_ORB_POSTPUBLICATION_V1_PASS_FOR_PROPF_MAPPING' if passed else 'QQQ_ORB_POSTPUBLICATION_V1_NO_GO'
    res={'status':status,'data':diag,'incomplete_session_count':len(incomplete),'incomplete_session_examples':incomplete[:20],
         'doji_skips':doji,'invalid_trade_count':invalid,'summaries':summaries,'gates':gate}
    (out/'RESULT.json').write_text(json.dumps(res,indent=2,allow_nan=False))
    print(json.dumps(res,indent=2,allow_nan=False))

if __name__=='__main__': main()
# technical timestamp-access fix only; frozen trading logic unchanged
