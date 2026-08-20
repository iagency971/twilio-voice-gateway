#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures as cf
import io, json, math, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

SYMBOL = 'BTCUSDT'
INTERVAL = '5m'
START = pd.Timestamp('2019-01-01', tz='UTC')
END = pd.Timestamp('2026-01-01', tz='UTC')  # 2026 sealed: do not cross.
BLOCKS = {
    'B00': (0, 8),
    'B08': (8, 16),
    'B16': (16, 24),
}
COSTS = {'PRIMARY': 5.0, 'STRESS': 10.0}  # basis points per side
COLS = ['open_time','open','high','low','close','volume','close_time','quote_volume',
        'trades','taker_base','taker_quote','ignore']


def month_iter():
    p = pd.Timestamp('2019-01-01')
    end = pd.Timestamp('2025-12-01')
    while p <= end:
        yield p.year, p.month
        p += pd.offsets.MonthBegin(1)


def fetch_month(item):
    y, m = item
    name = f'{SYMBOL}-{INTERVAL}-{y}-{m:02d}.zip'
    url = f'https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/{INTERVAL}/{name}'
    r = requests.get(url, timeout=120)
    if r.status_code != 200:
        return y, m, None, f'HTTP_{r.status_code}', len(r.content)
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        files = z.namelist()
        if not files:
            return y, m, None, 'EMPTY_ZIP', len(r.content)
        raw = z.read(files[0])
        df = pd.read_csv(io.BytesIO(raw), header=None, names=COLS)
        for c in ['open_time','open','high','low','close']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['open_time','open','high','low','close']).copy()
        ot = df['open_time'].astype('int64')
        unit = 'us' if int(ot.median()) > 10**14 else 'ms'
        df['utc'] = pd.to_datetime(ot, unit=unit, utc=True)
        return y, m, df[['utc','open','high','low','close']], 'OK', len(r.content)
    except Exception as e:
        return y, m, None, f'PARSE_{type(e).__name__}:{e}', len(r.content)


def load_data(out: Path, workers: int = 10):
    items = list(month_iter())
    frames, cov = [], []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_month, it) for it in items]
        for fut in cf.as_completed(futs):
            y, m, df, status, nbytes = fut.result()
            cov.append({'year':y,'month':m,'status':status,'bytes':nbytes})
            if df is not None:
                frames.append(df)
    coverage = pd.DataFrame(cov).sort_values(['year','month'])
    coverage.to_csv(out/'coverage.csv', index=False)
    bad = coverage[coverage.status.ne('OK')]
    if len(bad):
        raise RuntimeError(f'missing/invalid Binance months: {bad.to_dict(orient="records")[:10]}')
    d = pd.concat(frames, ignore_index=True).sort_values('utc').drop_duplicates('utc', keep='last')
    d = d[(d.utc >= START) & (d.utc < END)].copy()
    for c in ['open','high','low','close']:
        d[c] = d[c].astype(float)
    if d.empty or d.utc.max() >= END:
        raise RuntimeError('data boundary failure')
    diag = {
        'rows': int(len(d)), 'utc_min': str(d.utc.min()), 'utc_max': str(d.utc.max()),
        'months_ok': int(coverage.status.eq('OK').sum()), 'months_expected': int(len(items)),
        'sealed_2026': True,
    }
    (out/'data_diagnostics.json').write_text(json.dumps(diag, indent=2))
    return d, diag


def build_events(d: pd.DataFrame):
    x = d.copy()
    x['date'] = x.utc.dt.floor('D')
    events = []
    for date, g in x.groupby('date', sort=True):
        by_min = {int(t.hour*60+t.minute): row for t, (_, row) in zip(g.utc, g.iterrows())}
        for block, (sh, eh) in BLOCKS.items():
            s0 = sh*60
            signal_mins = list(range(s0, s0+30, 5))
            e0 = (eh*60 - 30) if eh < 24 else 23*60+30
            trade_mins = list(range(e0, e0+30, 5))
            if not all(m in by_min for m in signal_mins + trade_mins):
                continue
            sig = [by_min[m] for m in signal_mins]
            bars = [by_min[m] for m in trade_mins]
            sig_open = float(sig[0].open); sig_close = float(sig[-1].close)
            sig_range = float(max(r.high for r in sig) - min(r.low for r in sig))
            if sig_range <= 0 or sig_close == sig_open:
                continue
            side = 1 if sig_close > sig_open else -1
            events.append({
                'date': date, 'block': block, 'side': side, 'signal_return': sig_close/sig_open-1.0,
                'signal_range': sig_range,
                'bars': [(float(r.open),float(r.high),float(r.low),float(r.close)) for r in bars],
            })
    ev = pd.DataFrame(events)
    if ev.empty:
        return ev
    ev = ev.sort_values(['block','date']).reset_index(drop=True)
    ev['range_median20'] = ev.groupby('block')['signal_range'].transform(
        lambda s: s.shift(1).rolling(20, min_periods=20).median())
    ev['highvol'] = ev.signal_range.gt(ev.range_median20) & ev.range_median20.notna()
    return ev


def simulate_event(row, fee_bp_side: float):
    side = int(row.side); dist = float(row.signal_range); bars = row.bars
    entry = float(bars[0][0])
    stop = entry - dist if side == 1 else entry + dist
    exit_px = None; reason = None
    for i, (o,h,l,c) in enumerate(bars):
        if i > 0:
            if side == 1 and o <= stop:
                exit_px = o; reason = 'SL_GAP'; break
            if side == -1 and o >= stop:
                exit_px = o; reason = 'SL_GAP'; break
        if side == 1 and l <= stop:
            exit_px = stop; reason = 'SL'; break
        if side == -1 and h >= stop:
            exit_px = stop; reason = 'SL'; break
    if exit_px is None:
        exit_px = float(bars[-1][3]); reason = 'TIME'
    gross = side * (exit_px-entry) / dist
    cost_price = (fee_bp_side/10000.0) * (entry + exit_px)
    net = gross - cost_price/dist
    return {'entry':entry,'stop':stop,'exit':exit_px,'reason':reason,'gross_R':gross,'net_R':net}


def metrics(tr: pd.DataFrame):
    if tr.empty:
        return {'n':0,'mean':None,'sum':0.0,'pf':None,'max_dd':None,'positive_years':0,'active_years':0,'losing_streak':None}
    tr = tr.sort_values(['date']).copy(); r = tr.net_R.astype(float).to_numpy()
    pos = r[r>0].sum(); neg = -r[r<0].sum()
    pf = float(pos/neg) if neg>0 else (float('inf') if pos>0 else None)
    eq = np.cumsum(r); peak = np.maximum.accumulate(np.r_[0.0,eq])[:-1]
    maxdd = float(np.maximum(peak-eq,0).max(initial=0.0))
    cur=streak=0
    for v in r:
        if v<0: cur+=1; streak=max(streak,cur)
        else: cur=0
    y = tr.assign(year=pd.to_datetime(tr.date).dt.year).groupby('year').net_R.sum()
    return {'n':int(len(tr)),'mean':float(r.mean()),'sum':float(r.sum()),'pf':pf,'max_dd':maxdd,
            'positive_years':int((y>0).sum()),'active_years':int(len(y)),'losing_streak':int(streak),
            'annual':{str(int(k)):float(v) for k,v in y.items()}}


def candidate_events(ev, block, highvol, start_year, end_year):
    x = ev[(ev.block==block) & (ev.date.dt.year>=start_year) & (ev.date.dt.year<=end_year)].copy()
    if highvol:
        x = x[x.highvol].copy()
    return x


def simulate_frame(x, fee):
    rows=[]
    for _, r in x.iterrows():
        s=simulate_event(r, fee)
        s.update({'date':str(r.date.date()),'block':r.block,'side':'LONG' if r.side==1 else 'SHORT',
                  'signal_return':float(r.signal_return),'signal_range':float(r.signal_range),'highvol':bool(r.highvol)})
        rows.append(s)
    return pd.DataFrame(rows)


def main():
    out=Path('btc-propf/results/session_momentum_v1'); out.mkdir(parents=True, exist_ok=True)
    try:
        d,diag=load_data(out)
        ev=build_events(d)
        if ev.empty: raise RuntimeError('no events')
        # DEV selection: validation outcomes are not computed here.
        grid=[]; dev_trades={}
        for block in BLOCKS:
            for highvol in [False, True]:
                name=f'{block}_{"HIGHVOL" if highvol else "ALL"}'
                x=candidate_events(ev,block,highvol,2019,2023)
                tr=simulate_frame(x,COSTS['PRIMARY']); dev_trades[name]=tr
                m=metrics(tr)
                eligible=(m['n']>=400 and m['mean'] is not None and m['mean']>=0.05 and m['pf'] is not None and m['pf']>=1.10
                          and m['positive_years']>=3 and m['max_dd'] is not None and m['max_dd']<=25.0)
                score=(m['mean']*math.sqrt(m['n'])) if eligible else -999.0
                grid.append({'candidate':name,'block':block,'highvol':highvol,'eligible':eligible,'score':score,**{k:v for k,v in m.items() if k!='annual'}})
        gd=pd.DataFrame(grid).sort_values(['eligible','score','candidate'],ascending=[False,False,True]); gd.to_csv(out/'dev_grid.csv',index=False)
        elig=gd[gd.eligible]
        if elig.empty:
            result={'status':'BTC_SESSION_MOMENTUM_V1_DEV_NO_GO','data':diag,'n_candidates':6,'n_eligible':0}
            (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2)); return
        sel=elig.iloc[0]; name=str(sel.candidate); block=str(sel.block); highvol=bool(sel.highvol)
        dev_trades[name].to_csv(out/'selected_dev_trades.csv',index=False)
        selected_dev=metrics(dev_trades[name])
        freeze={'candidate':name,'block':block,'highvol':highvol,'selection_score':float(sel.score),'dev_metrics':selected_dev}
        (out/'SELECTED_PREVALIDATION.json').write_text(json.dumps(freeze,indent=2))
        # Temporal validation is opened only for the selected candidate.
        xv=candidate_events(ev,block,highvol,2024,2025)
        vp=simulate_frame(xv,COSTS['PRIMARY']); vs=simulate_frame(xv,COSTS['STRESS'])
        vp.to_csv(out/'validation_primary_trades.csv',index=False); vs.to_csv(out/'validation_stress_trades.csv',index=False)
        mp=metrics(vp); ms=metrics(vs)
        val_pass=(mp['n']>=150 and mp['mean'] is not None and mp['mean']>=0.05 and mp['pf'] is not None and mp['pf']>=1.10
                  and mp['positive_years']==2 and mp['active_years']==2 and mp['max_dd'] is not None and mp['max_dd']<=15.0
                  and ms['mean'] is not None and ms['mean']>0 and ms['pf'] is not None and ms['pf']>1.00)
        status='BTC_SESSION_MOMENTUM_V1_READY_FOR_2026_OOS_FREEZE' if val_pass else 'BTC_SESSION_MOMENTUM_V1_VALIDATION_NO_GO'
        result={'status':status,'data':diag,'selected':freeze,'validation_primary':mp,'validation_stress':ms,
                'validation_pass':val_pass,'oos_2026_opened':False}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
    except Exception as e:
        result={'status':'BTC_SESSION_MOMENTUM_V1_INVALID_ABORT','error':repr(e),'oos_2026_opened':False}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2)); raise

if __name__=='__main__': main()
