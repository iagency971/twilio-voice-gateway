#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

WINDOWS = {
    'H1': (pd.Timestamp('2024-08-01T00:00:00Z'), pd.Timestamp('2025-08-01T00:00:00Z')),
    'H2': (pd.Timestamp('2025-08-01T00:00:00Z'), pd.Timestamp('2026-08-01T00:00:00Z')),
}
SLIPPAGE = (0.00, 0.02, 0.05, 0.10)
COMMISSION_RATE_SIDE = 0.000007
EPS = 1e-10


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--bid-files', nargs='+', required=True)
    p.add_argument('--ask-files', nargs='+', required=True)
    p.add_argument('--trade-files', nargs='+', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--trades-output', required=True)
    p.add_argument('--ask-manifest-output', required=True)
    return p.parse_args()


def load_side(files, side):
    frames = []
    manifest = []
    import hashlib
    for f in sorted(files):
        p = Path(f)
        b = p.read_bytes()
        manifest.append({'file': p.name, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)})
        d = pd.read_csv(p)
        if not {'timestamp','open','high','low','close'} <= set(d.columns):
            raise RuntimeError(f'bad schema {p}')
        d = d[['timestamp','open','high','low','close']].copy()
        d['time'] = pd.to_datetime(d['timestamp'], unit='ms', utc=True)
        d = d.drop(columns=['timestamp'])
        for c in ('open','high','low','close'):
            d[c] = pd.to_numeric(d[c], errors='coerce')
        d = d.rename(columns={c:f'{c}_{side}' for c in ('open','high','low','close')})
        frames.append(d)
    out = pd.concat(frames, ignore_index=True).sort_values('time').reset_index(drop=True)
    if out.time.duplicated().any():
        raise RuntimeError(f'duplicate {side} timestamps')
    return out, manifest


def active_merge(bid, ask):
    m = bid.merge(ask, on='time', how='inner', validate='one_to_one')
    cols = [f'{c}_{s}' for s in ('bid','ask') for c in ('open','high','low','close')]
    good = np.ones(len(m), dtype=bool)
    for c in cols:
        x = m[c].to_numpy(float)
        good &= np.isfinite(x) & (x > 0)
    return m.loc[good].sort_values('time').reset_index(drop=True)


def infer_session(path):
    n = Path(path).name.upper()
    if 'ASIA_CORE_STANDALONE' in n: return 'ASIA_CORE_STANDALONE'
    if 'ASIA_BROAD' in n: return 'ASIA_BROAD'
    if n.startswith('EUROPE_') or 'EUROPE_Z4' in n: return 'EUROPE'
    if n.startswith('US_') or 'US_Z4' in n: return 'US'
    raise RuntimeError(f'cannot infer session from {path}')


def load_trade_file(path):
    p = Path(path)
    d = pd.read_csv(p, compression='gzip' if p.suffix == '.gz' else None)
    d['session'] = infer_session(path)
    d['entry_time'] = pd.to_datetime(d.entry_time, utc=True)
    d['trigger_time'] = pd.to_datetime(d.trigger_time, utc=True)
    return d


def in_session(t, name):
    h = pd.Timestamp(t).tz_convert('America/New_York').hour
    if name == 'US': return 8 <= h < 17
    if name == 'ASIA_BROAD': return h >= 18 or h < 3
    if name == 'ASIA_CORE_STANDALONE': return h >= 21 or h < 3
    if name == 'EUROPE': return 3 <= h < 8
    raise ValueError(name)


def session_id(t, name):
    q = pd.Timestamp(t).tz_convert('America/New_York')
    if not in_session(t, name): return None
    if name in ('ASIA_BROAD','ASIA_CORE_STANDALONE') and q.hour < 3:
        return (q.date() - pd.Timedelta(days=1)).isoformat()
    return q.date().isoformat()


def quant(x):
    a = np.asarray(list(x), float)
    a = a[np.isfinite(a)]
    if len(a) == 0: return {'n':0,'mean':None,'median':None,'p90':None,'p95':None,'p99':None}
    return {'n':int(len(a)), 'mean':float(a.mean()), 'median':float(np.median(a)),
            'p90':float(np.quantile(a,.90)), 'p95':float(np.quantile(a,.95)), 'p99':float(np.quantile(a,.99))}


def summary(df, rcol='net_R'):
    if len(df) == 0:
        return {'n':0,'mean_R':None,'profit_factor_R':None,'outcomes':{}}
    r = df[rcol].to_numpy(float)
    pos = r[r>0].sum(); neg = -r[r<0].sum()
    return {'n':int(len(df)), 'mean_R':float(r.mean()),
            'profit_factor_R':float(pos/neg) if neg>0 else (float('inf') if pos>0 else None),
            'outcomes':{str(k):int(v) for k,v in Counter(df.exec_outcome.astype(str)).items()}}


def one_position(df):
    keep=[]
    for (sess,sid),g in df.sort_values('entry_time').groupby(['session','session_id'], sort=True):
        last_exit=None
        for idx,r in g.sort_values('entry_time').iterrows():
            et=pd.Timestamp(r.entry_time)
            if last_exit is None or et > last_exit:
                keep.append(idx)
                last_exit=pd.Timestamp(r.exec_exit_time)
    return df.loc[keep].sort_values(['session','entry_time']).copy()


def main():
    a=args()
    bid,bid_manifest=load_side(a.bid_files,'bid')
    ask,ask_manifest=load_side(a.ask_files,'ask')
    m=active_merge(bid,ask)
    if len(m)==0: raise RuntimeError('empty active BID/ASK merge')
    idx_by_time={pd.Timestamp(t):i for i,t in enumerate(m.time)}

    # Session endpoints over the merged executable market.
    end_by_key={}
    for s in ('US','ASIA_BROAD','ASIA_CORE_STANDALONE','EUROPE'):
        pairs=[]
        for i,t in enumerate(m.time):
            sid=session_id(t,s)
            if sid is not None: pairs.append((sid,i))
        for sid,i in pairs: end_by_key[(s,sid)]=i

    src=pd.concat([load_trade_file(f) for f in a.trade_files], ignore_index=True)
    out=[]
    entry_parity=[]
    for _,tr in src.sort_values(['session','entry_time']).iterrows():
        s=str(tr.session); sid=str(tr.session_id); et=pd.Timestamp(tr.entry_time)
        if et not in idx_by_time: raise RuntimeError(f'missing executable entry timestamp {s} {et}')
        i0=idx_by_time[et]
        i1=end_by_key.get((s,sid))
        if i1 is None or i1 < i0: raise RuntimeError(f'missing session end {s} {sid}')
        entry=float(m.at[i0,'open_bid'])
        entry_parity.append(abs(entry-float(tr.entry_price)))
        if abs(entry-float(tr.entry_price)) > 1e-6:
            raise RuntimeError(f'BID entry parity failure {s} {et}: {entry} vs {tr.entry_price}')
        target=float(tr.target_price); stop=float(tr.stop_price)
        risk=stop-entry
        if not np.isfinite(risk) or risk <= EPS: raise RuntimeError(f'nonpositive risk {s} {et}')
        exec_out='SESSION_LIQUIDATION'; exi=i1; exitp=float(m.at[i1,'close_ask'])
        for k in range(i0,i1+1):
            tp=float(m.at[k,'low_ask']) <= target + EPS
            inv=float(m.at[k,'close_bid']) > stop + EPS
            if inv:  # conservative if both true
                exec_out='INVALIDATION'; exi=k; exitp=float(m.at[k,'close_ask']); break
            if tp:
                exec_out='TP'; exi=k; exitp=target; break
        gross_pnl=entry-exitp
        gross_R=gross_pnl/risk
        commission=COMMISSION_RATE_SIDE*(entry+exitp)
        net_R=(gross_pnl-commission)/risk
        row={
            'session':s,'session_id':sid,'trigger_time':pd.Timestamp(tr.trigger_time),'entry_time':et,
            'entry_bid':entry,'target':target,'stop':stop,'risk_usd_per_oz':risk,
            'exec_outcome':exec_out,'exec_exit_time':pd.Timestamp(m.at[exi,'time']),'exec_exit_price':exitp,
            'gross_pnl_usd_per_oz':gross_pnl,'gross_R':gross_R,'commission_usd_per_oz':commission,'net_R':net_R,
            'entry_spread_usd':float(m.at[i0,'open_ask']-m.at[i0,'open_bid']),
            'exit_close_spread_context_usd':float(m.at[exi,'close_ask']-m.at[exi,'close_bid']),
        }
        for slip in SLIPPAGE:
            row[f'net_R_slip_{slip:.2f}']=(gross_pnl-commission-slip)/risk
        out.append(row)
    d=pd.DataFrame(out)
    if len(d)!=len(src): raise RuntimeError('trade count mismatch')
    one=one_position(d)

    result={
        'status':'Z4_GAP_BR70_DUKASCOPY_BIDASK_FTMO_COMMISSION_EXECUTION_COMPLETE',
        'source_commit':'3fbaf3280338474b379e3a01ac3396f85d4a60be',
        'commission_rate_per_side':COMMISSION_RATE_SIDE,
        'source_trade_count':int(len(src)),'executable_trade_count':int(len(d)),
        'bid_rows':int(len(bid)),'ask_rows':int(len(ask)),'active_inner_join_rows':int(len(m)),
        'entry_bid_parity_max_abs':float(max(entry_parity) if entry_parity else 0.0),
        'spread_entry_distribution_all':quant(d.entry_spread_usd),
        'spread_exit_close_context_distribution_all':quant(d.exit_close_spread_context_usd),
        'risk_distribution_all':quant(d.risk_usd_per_oz),
        'by_session':{},'pooled_descriptive':{},'gate':{},
        'explicit_nonclaim':'Dukascopy historical BID/ASK spread is not claimed to equal historical FTMO spread. FTMO current commission is applied separately.'
    }
    positive_both=[]
    for s in ('US','ASIA_BROAD','ASIA_CORE_STANDALONE','EUROPE'):
        result['by_session'][s]={}
        for h,(lo,hi) in WINDOWS.items():
            x=d[(d.session==s)&(d.entry_time>=lo)&(d.entry_time<hi)]
            xo=one[(one.session==s)&(one.entry_time>=lo)&(one.entry_time<hi)]
            z={'all':{'gross':summary(x,'gross_R'),'net_commission':summary(x,'net_R')},
               'one_position':{'gross':summary(xo,'gross_R'),'net_commission':summary(xo,'net_R')},
               'entry_spread':quant(x.entry_spread_usd),'risk_usd_per_oz':quant(x.risk_usd_per_oz)}
            for slip in SLIPPAGE:
                z['all'][f'net_commission_plus_slip_{slip:.2f}']=summary(x,f'net_R_slip_{slip:.2f}')
                z['one_position'][f'net_commission_plus_slip_{slip:.2f}']=summary(xo,f'net_R_slip_{slip:.2f}')
            result['by_session'][s][h]=z
        hb=[result['by_session'][s][h]['one_position']['net_commission']['mean_R'] for h in ('H1','H2')]
        if all(v is not None and v>0 for v in hb): positive_both.append(s)
    for h,(lo,hi) in WINDOWS.items():
        x=d[(d.entry_time>=lo)&(d.entry_time<hi)]; xo=one[(one.entry_time>=lo)&(one.entry_time<hi)]
        result['pooled_descriptive'][h]={'all_net_commission':summary(x,'net_R'),'one_position_net_commission':summary(xo,'net_R')}
        for slip in SLIPPAGE:
            result['pooled_descriptive'][h][f'one_position_net_commission_plus_slip_{slip:.2f}']=summary(xo,f'net_R_slip_{slip:.2f}')
    pooled_ok=all(result['pooled_descriptive'][h]['one_position_net_commission']['mean_R'] is not None and result['pooled_descriptive'][h]['one_position_net_commission']['mean_R']>0 for h in ('H1','H2'))
    result['gate']={'sessions_positive_both_halves_one_position_net_commission':positive_both,
                    'session_count':len(positive_both),'pooled_positive_both_halves':bool(pooled_ok),
                    'confirmation_candidate':bool(pooled_ok and len(positive_both)>=3),
                    'production_authorization':'NONE_RETROSPECTIVE_BIDASK_EXECUTION_VALIDATION'}
    Path(a.output).write_text(json.dumps(result,indent=2,default=str))
    d.to_csv(a.trades_output,index=False,compression='gzip')
    Path(a.ask_manifest_output).write_text(json.dumps({'source_commit':result['source_commit'],'ask_files':ask_manifest,'bid_files':bid_manifest},indent=2))
    print(json.dumps({'status':result['status'],'gate':result['gate'],'entry_spread':result['spread_entry_distribution_all'],'pooled':result['pooled_descriptive']},indent=2))

if __name__=='__main__': main()
