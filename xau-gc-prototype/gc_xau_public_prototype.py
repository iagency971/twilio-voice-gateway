#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, time
from pathlib import Path
import numpy as np
import pandas as pd
import requests

GC_URL = 'https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/GC/GC_1min_20260120_20260415.csv'
XAU_TMPL = 'https://raw.githubusercontent.com/kevingtlin/dukascopy_XAUUSD_1m_Data/main/xauusd/{side}/m1/xauusd_{side}_m1_2026_{month:02d}.csv'

def dl(url: str, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 1000: return
    err=None
    for k in range(4):
        try:
            with requests.get(url, stream=True, timeout=90) as r:
                r.raise_for_status(); tmp=dst.with_suffix(dst.suffix+'.part')
                with tmp.open('wb') as f:
                    for ch in r.iter_content(1024*1024):
                        if ch: f.write(ch)
                tmp.replace(dst); return
        except Exception as e:
            err=e; time.sleep(2*(k+1))
    raise RuntimeError(f'download failed {url}: {err}')

def sha(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for ch in iter(lambda:f.read(1024*1024),b''): h.update(ch)
    return h.hexdigest()

def load_xau(files_bid, files_ask):
    out=[]
    for bp,ap in zip(files_bid,files_ask):
        b=pd.read_csv(bp); a=pd.read_csv(ap)
        for d in (b,a):
            d['timestamp']=pd.to_datetime(d['timestamp'],unit='ms',utc=True,errors='raise')
        m=b.merge(a,on='timestamp',suffixes=('_bid','_ask'),how='inner')
        for c in ['open','high','low','close']:
            m[c]=(pd.to_numeric(m[f'{c}_bid'])+pd.to_numeric(m[f'{c}_ask']))/2
        m['spread']=pd.to_numeric(m['close_ask'])-pd.to_numeric(m['close_bid'])
        out.append(m[['timestamp','open','high','low','close','spread']])
    x=pd.concat(out,ignore_index=True).sort_values('timestamp').drop_duplicates('timestamp')
    return x.set_index('timestamp',drop=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='outputs/gc_xau_public'); args=ap.parse_args()
    out=Path(args.out); raw=out/'raw'; out.mkdir(parents=True,exist_ok=True); raw.mkdir(parents=True,exist_ok=True)
    gcpath=raw/'GC_1min_20260120_20260415.csv'; dl(GC_URL,gcpath)
    bids=[]; asks=[]
    for mo in range(1,5):
        bp=raw/f'xauusd_bid_m1_2026_{mo:02d}.csv'; apath=raw/f'xauusd_ask_m1_2026_{mo:02d}.csv'
        dl(XAU_TMPL.format(side='bid',month=mo),bp); dl(XAU_TMPL.format(side='ask',month=mo),apath)
        bids.append(bp); asks.append(apath)
    x=load_xau(bids,asks)
    g=pd.read_csv(gcpath)
    req=['datetime','open','high','low','close','volume']; missing=[c for c in req if c not in g.columns]
    if missing: raise RuntimeError(f'GC missing {missing}')
    g['timestamp']=pd.to_datetime(g.datetime,utc=True,errors='raise')
    for c in ['open','high','low','close','volume']: g[c]=pd.to_numeric(g[c],errors='raise')
    g=g.sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp',drop=False)
    ix=g.index.intersection(x.index).sort_values()
    z=pd.DataFrame(index=ix)
    z['gc_close']=g.loc[ix,'close']; z['gc_volume']=g.loc[ix,'volume']; z['xau_close']=x.loc[ix,'close']; z['xau_spread']=x.loc[ix,'spread']
    z['basis_raw']=z.gc_close-z.xau_close
    z['gc_ret']=z.gc_close.pct_change(fill_method=None); z['xau_ret']=z.xau_close.pct_change(fill_method=None)
    pre=z.basis_raw.shift(1); z['basis_med15_pre']=pre.rolling(15,min_periods=15).median()
    z['basis_mad15_pre']=pre.rolling(15,min_periods=15).apply(lambda q: float(np.median(np.abs(q-np.median(q)))),raw=True)
    vpre=z.gc_volume.shift(1); vbase=z.gc_volume.shift(2).rolling(60,min_periods=60).median().replace(0,np.nan)
    z['gc_volume_pre1']=vpre; z['gc_volume_rel60_pre']=vpre/vbase
    ret=z[['gc_ret','xau_ret']].dropna(); corr=float(ret.corr().iloc[0,1]) if len(ret)>=10 else None
    b=z.basis_raw.dropna()
    d=z.assign(day=z.index.floor('D')).groupby('day').agg(rows=('basis_raw','size'),basis_median=('basis_raw','median'),basis_std=('basis_raw','std'),gc_volume=('gc_volume','sum'),xau_spread_median=('xau_spread','median')).reset_index()
    d.to_csv(out/'basis_daily.csv',index=False)
    z[['gc_close','gc_volume','xau_close','xau_spread','basis_raw','basis_med15_pre','basis_mad15_pre','gc_volume_pre1','gc_volume_rel60_pre']].to_csv(out/'aligned_causal_features.csv',index_label='timestamp')
    summary={
      'data_role':'PIPELINE_PROTOTYPE_NOT_FINAL_RESEARCH_SOURCE',
      'gc_source':'TopstepX ProjectX mirror; fixed contract CON.F.US.GCE.J26',
      'gc_contract':'GCJ26 / Apr-2026',
      'gc_rows':int(len(g)),'xau_rows':int(len(x)),'overlap_rows':int(len(z)),
      'first_overlap_utc':str(z.index.min()),'last_overlap_utc':str(z.index.max()),
      'overlap_fraction_gc':float(len(z)/len(g)) if len(g) else None,
      'return_corr_1m':corr,
      'basis_median':float(b.median()),'basis_mean':float(b.mean()),'basis_std':float(b.std()),
      'basis_p01':float(b.quantile(.01)),'basis_p05':float(b.quantile(.05)),'basis_p95':float(b.quantile(.95)),'basis_p99':float(b.quantile(.99)),
      'basis_abs_change_p95':float(z.basis_raw.diff().abs().quantile(.95)),
      'gc_volume_total':float(z.gc_volume.sum()),'gc_nonzero_volume_fraction':float((z.gc_volume>0).mean()),
      'xau_spread_median':float(z.xau_spread.median()),'xau_spread_p95':float(z.xau_spread.quantile(.95)),
      'causal_feature_rows':int(z.basis_med15_pre.notna().sum()),
      'causal_rule':'features at minute t use information no later than t-1',
      'files_sha256':{'gc':sha(gcpath),**{p.name:sha(p) for p in bids+asks}},
    }
    (out/'alignment_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
