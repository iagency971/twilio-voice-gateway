#!/usr/bin/env python3
from __future__ import annotations

import io, json, math
from pathlib import Path
import requests
import numpy as np
import pandas as pd

URLS = [
    ('HIST', 'https://raw.githubusercontent.com/lvrusu/QQQ_price_data/main/QQQ5m_regular_raw_01_01_2000_to_04_10_2024.csv', 0),
    ('EXT', 'https://raw.githubusercontent.com/lvrusu/QQQ_price_data/main/QQQ5m_Ext_J_23_to_Mar_20a_2026.csv', 1),
]
SCENARIOS = {
    'SOURCE_COST': 0.5,
    'DOUBLE_COST': 1.0,
    'HARD_STRESS': 2.0,
}
WINDOWS = {
    'BACKGROUND': ('2000-01-01','2010-01-01'),
    'SOURCE_IS_PROXY': ('2010-01-01','2018-01-01'),
    'SOURCE_OOS_PROXY_FULL_YEARS': ('2018-01-01','2026-01-01'),
    'RECENT_FULL_YEARS': ('2023-01-01','2026-01-01'),
    'PARTIAL_2026': ('2026-01-01','2027-01-01'),
    'SOURCE_OOS_PROXY_ALL': ('2018-01-01','2027-01-01'),
}


def normalize(raw: bytes, tag: str, priority: int):
    df = pd.read_csv(io.BytesIO(raw))
    lookup = {str(c).strip().lower(): c for c in df.columns}
    dtc = lookup.get('ds') or lookup.get('datetime') or lookup.get('date') or lookup.get('timestamp')
    if dtc is None:
        raise RuntimeError(f'{tag}: datetime column missing: {list(df.columns)}')
    ren = {dtc:'dt'}
    for w in ['open','high','low','close']:
        c=lookup.get(w)
        if c is None: raise RuntimeError(f'{tag}: {w} missing')
        ren[c]=w
    df=df.rename(columns=ren)
    if 'unique_id' in lookup:
        ucol=lookup['unique_id']
        if ucol in df.columns:
            df=df[df[ucol].astype(str).str.upper().eq('QQQ')]
    df['dt']=pd.to_datetime(df['dt'], errors='coerce')
    for c in ['open','high','low','close']:
        df[c]=pd.to_numeric(df[c], errors='coerce')
    df=df.dropna(subset=['dt','open','high','low','close']).copy()
    df['priority']=priority; df['source']=tag
    return df[['dt','open','high','low','close','priority','source']]


def load_data(out: Path):
    frames=[]; diag=[]
    for tag,url,p in URLS:
        r=requests.get(url,timeout=180)
        r.raise_for_status()
        if len(r.content)<100000:
            raise RuntimeError(f'{tag}: unexpectedly small download {len(r.content)}')
        f=normalize(r.content,tag,p); frames.append(f)
        diag.append({'tag':tag,'url':url,'bytes':len(r.content),'rows_normalized':int(len(f)),
                     'dt_min':str(f.dt.min()),'dt_max':str(f.dt.max())})
    d=pd.concat(frames,ignore_index=True)
    d=d.sort_values(['dt','priority']).drop_duplicates('dt',keep='last').sort_values('dt').reset_index(drop=True)
    d['date']=d.dt.dt.normalize()
    d['minute']=d.dt.dt.hour*60+d.dt.dt.minute
    d=d[(d.minute>=570)&(d.minute<=955)].copy()
    result={'sources':diag,'combined_rows_rth':int(len(d)),'dt_min':str(d.dt.min()),'dt_max':str(d.dt.max()),
            'duplicates_after_merge':int(d.dt.duplicated().sum())}
    (out/'data_diagnostics.json').write_text(json.dumps(result,indent=2))
    return d,result


def build_daily(d: pd.DataFrame, out: Path):
    rows=[]; rejected=[]
    for date,g in d.groupby('date',sort=True):
        g=g.sort_values('minute').drop_duplicates('minute',keep='last')
        mins=g.minute.astype(int).tolist()
        if not mins or mins[0]!=570 or mins[-1]<775:
            rejected.append({'date':str(date.date()),'reason':'bad_session_bounds','n':len(mins)}); continue
        expected=list(range(570,mins[-1]+1,5))
        if mins!=expected:
            rejected.append({'date':str(date.date()),'reason':'non_contiguous','n':len(mins),'last_min':mins[-1]}); continue
        rows.append({'date':date,'open':float(g.iloc[0].open),'high':float(g.high.max()),'low':float(g.low.min()),
                     'close':float(g.iloc[-1].close),'bars':int(len(g)),'last_min':int(mins[-1])})
    daily=pd.DataFrame(rows).set_index('date').sort_index()
    daily['sma200']=daily.close.rolling(200,min_periods=200).mean()
    pc=daily.close.shift(1)
    tr=pd.concat([(daily.high-daily.low),(daily.high-pc).abs(),(daily.low-pc).abs()],axis=1).max(axis=1)
    daily['atr14']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    daily['prior_close']=daily.close.shift(1)
    daily['prior_sma200']=daily.sma200.shift(1)
    daily['prior_atr14']=daily.atr14.shift(1)
    daily.reset_index().to_csv(out/'daily_features.csv',index=False)
    pd.DataFrame(rejected).to_csv(out/'daily_rejected_sessions.csv',index=False)
    return daily,rejected


def simulate_trade(g: pd.DataFrame, prior_atr: float, bp_side: float):
    b1=g[g.minute.eq(575)]
    eod=g[g.minute.eq(955)]
    if len(b1)!=1 or len(eod)!=1: return None
    b1=b1.iloc[0]; eod=eod.iloc[0]
    entry=float(b1.open); dist=0.05*float(prior_atr)
    if not np.isfinite(dist) or dist<=0: return None
    stop=entry-dist
    bars=g[(g.minute>=575)&(g.minute<=955)].sort_values('minute')
    exit_px=None; exit_dt=None; reason=None
    for k,(_,b) in enumerate(bars.iterrows()):
        o,h,l,c=map(float,[b.open,b.high,b.low,b.close])
        if k>0 and o<=stop:
            exit_px=o; exit_dt=b['dt']; reason='SL_GAP'; break
        if l<=stop:
            exit_px=stop; exit_dt=b['dt']; reason='SL'; break
    if exit_px is None:
        exit_px=float(eod.close); exit_dt=eod['dt']; reason='TIME'
    gross=(exit_px-entry)/dist
    cost=((bp_side/10000.0)*entry+(bp_side/10000.0)*exit_px)/dist
    return {'entry_time':str(b1['dt']),'exit_time':str(exit_dt),'entry':entry,'stop':stop,'stop_dist':dist,
            'exit':exit_px,'exit_reason':reason,'gross_R':gross,'cost_R':cost,'net_R':gross-cost}


def metrics(x: pd.DataFrame):
    if x.empty:
        return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None,'losing_streak':None,
                'avg_win':None,'avg_loss':None}
    x=x.sort_values('date'); r=x.net_R.astype(float).to_numpy()
    pos=r[r>0]; neg=r[r<0]; ps=pos.sum(); ns=-neg.sum()
    pf=float(ps/ns) if ns>0 else (float('inf') if ps>0 else None)
    eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0.0,eq])[:-1]; dd=np.maximum(peak-eq,0)
    cur=streak=0
    for v in r:
        if v<0: cur+=1; streak=max(streak,cur)
        else: cur=0
    return {'n':int(len(r)),'mean':float(r.mean()),'sum':float(r.sum()),'pf':pf,'win_rate':float((r>0).mean()),
            'max_dd':float(dd.max(initial=0.0)),'losing_streak':int(streak),
            'avg_win':float(pos.mean()) if len(pos) else None,'avg_loss':float(neg.mean()) if len(neg) else None}


def window_metrics(tr: pd.DataFrame, start: str, end: str):
    x=tr[(tr.date>=pd.Timestamp(start))&(tr.date<pd.Timestamp(end))].copy()
    return metrics(x)


def main():
    out=Path('qqq-formed/results/v1'); out.mkdir(parents=True,exist_ok=True)
    try:
        d,diag=load_data(out); daily,rejected=build_daily(d,out)
        rows=[]; skips={'missing_trade_bars':0,'not_bullish':0,'features_unavailable':0,'trend_filter':0}
        for date,g in d.groupby('date',sort=True):
            g=g.sort_values('minute').drop_duplicates('minute',keep='last')
            b0=g[g.minute.eq(570)]; b1=g[g.minute.eq(575)]; eod=g[g.minute.eq(955)]
            if len(b0)!=1 or len(b1)!=1 or len(eod)!=1:
                skips['missing_trade_bars']+=1; continue
            b0=b0.iloc[0]
            if not float(b0.close)>float(b0.open):
                skips['not_bullish']+=1; continue
            if date not in daily.index:
                skips['features_unavailable']+=1; continue
            f=daily.loc[date]
            if pd.isna(f.prior_close) or pd.isna(f.prior_sma200) or pd.isna(f.prior_atr14):
                skips['features_unavailable']+=1; continue
            if not float(f.prior_close)>float(f.prior_sma200):
                skips['trend_filter']+=1; continue
            for sc,bp in SCENARIOS.items():
                r=simulate_trade(g,float(f.prior_atr14),bp)
                if r is None:
                    skips['missing_trade_bars']+=1; continue
                r.update({'date':date,'scenario':sc,'first_open':float(b0.open),'first_close':float(b0.close),
                          'prior_close':float(f.prior_close),'prior_sma200':float(f.prior_sma200),'prior_atr14':float(f.prior_atr14)})
                rows.append(r)
        tr=pd.DataFrame(rows)
        if tr.empty: raise RuntimeError('no trades after rules')
        tr['date']=pd.to_datetime(tr['date'])
        tr.to_csv(out/'trades.csv',index=False)
        summary={}; annual=[]
        for sc in SCENARIOS:
            x=tr[tr.scenario.eq(sc)].copy()
            wm={k:window_metrics(x,*v) for k,v in WINDOWS.items()}
            summary[sc]=wm
            for y,g in x.assign(year=x['date'].dt.year).groupby('year'):
                mm=metrics(g); mm.update({'scenario':sc,'year':int(y)}); annual.append(mm)
        pd.DataFrame(annual).to_csv(out/'annual_metrics.csv',index=False)
        src=tr[tr.scenario.eq('SOURCE_COST')].copy()
        annual_src=src.assign(year=src['date'].dt.year).groupby('year').net_R.sum()
        full_years=annual_src[(annual_src.index>=2018)&(annual_src.index<=2025)]
        pos_full=int((full_years>0).sum())
        is_m=summary['SOURCE_COST']['SOURCE_IS_PROXY']
        oos=summary['SOURCE_COST']['SOURCE_OOS_PROXY_FULL_YEARS']
        recent=summary['SOURCE_COST']['RECENT_FULL_YEARS']
        dbl=summary['DOUBLE_COST']['SOURCE_OOS_PROXY_FULL_YEARS']
        gates={
            'is_mean_positive':is_m['mean'] is not None and is_m['mean']>0,
            'is_pf_ge_1_15':is_m['pf'] is not None and is_m['pf']>=1.15,
            'oos_n_ge_500':oos['n']>=500,
            'oos_mean_positive':oos['mean'] is not None and oos['mean']>0,
            'oos_pf_ge_1_15':oos['pf'] is not None and oos['pf']>=1.15,
            'oos_positive_years_ge_6_of_8':pos_full>=6,
            'oos_dd_le_20R':oos['max_dd'] is not None and oos['max_dd']<=20,
            'double_cost_oos_mean_positive':dbl['mean'] is not None and dbl['mean']>0,
            'double_cost_oos_pf_gt_1_05':dbl['pf'] is not None and dbl['pf']>1.05,
            'recent_2023_2025_mean_nonnegative':recent['mean'] is not None and recent['mean']>=0,
            'recent_2023_2025_pf_ge_1':recent['pf'] is not None and recent['pf']>=1.0,
        }
        passed=all(gates.values())
        status='QQQ_FORMED_OPENMOVE_V1_PASS_FOR_1M_NQ_REPLICATION' if passed else 'QQQ_FORMED_OPENMOVE_V1_NO_GO'
        result={'status':status,'data':diag,'daily_complete_sessions':int(len(daily)),'daily_rejected_count':len(rejected),
                'skips':skips,'positive_oos_full_years_2018_2025':pos_full,'oos_full_year_totals':{str(int(k)):float(v) for k,v in full_years.items()},
                'summary':summary,'gates':gates,'interpretation':'QQQ 5m cross-source proxy replication only; not NQ/US100 live validation.'}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False))
        print(json.dumps(result,indent=2,allow_nan=False))
    except Exception as e:
        result={'status':'QQQ_FORMED_OPENMOVE_V1_INVALID_ABORT','error':repr(e)}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2)); raise

if __name__=='__main__': main()
