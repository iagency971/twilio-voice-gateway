#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

r=load_module('dual_session_runner',HERE/'xau_ebuy_c1_refresh_causal_reaction_v1_2_session.py')
d=load_module('dual_parent_v10',HERE/'xau_ebuy_c1_refresh_dual_c5_postprocess_v1_0.py')
cs=load_module('dual_common_support_for_days',HERE/'xau_ebuy_c1_refresh_common_support_postprocess_v1_0.py')


def day_counts_all(trades,all_days):
    out={str(x):{'tp':0,'resolved':0} for x in all_days}
    for row in trades:
        if not bool(row.get('fired')): continue
        day=str(row.get('ny_day')); q=out.setdefault(day,{'tp':0,'resolved':0})
        st=str(row.get('tp1_invalidation_status'))
        if st in r.AMBIG: continue
        q['resolved']+=1
        if st=='TP1_FIRST': q['tp']+=1
    return out


def paired_day_bootstrap_all(c1_trades,c5_trades,all_days):
    days=[str(x) for x in all_days]
    if not days:
        return {'n_days':0,'delta_tp1_rate':None,'bootstrap_95':[None,None],'seed':r.BOOT_SEED,'replicates':r.BOOT_N,'all_common_days_included':True}
    a=day_counts_all(c1_trades,days);b=day_counts_all(c5_trades,days)
    z=np.asarray([(a[x]['tp'],a[x]['resolved'],b[x]['tp'],b[x]['resolved']) for x in days],int)
    d1=z[:,1].sum();d5=z[:,3].sum();p1=z[:,0].sum()/d1 if d1 else np.nan;p5=z[:,2].sum()/d5 if d5 else np.nan
    rng=np.random.default_rng(r.BOOT_SEED);vals=[];n=len(days)
    for _ in range(r.BOOT_N):
        q=z[rng.integers(0,n,size=n)];q1=q[:,1].sum();q5=q[:,3].sum()
        if q1 and q5: vals.append(q[:,0].sum()/q1-q[:,2].sum()/q5)
    return {'n_days':int(n),'delta_tp1_rate':float(p1-p5) if np.isfinite(p1) and np.isfinite(p5) else None,
            'bootstrap_95':[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if vals else [None,None],
            'seed':r.BOOT_SEED,'replicates':r.BOOT_N,'all_common_days_included':True,
            'C1_resolved_total':int(d1),'C5_resolved_total':int(d5)}


def cli_value(flag):
    i=sys.argv.index(flag);return sys.argv[i+1]


def cli_files():
    i=sys.argv.index('--files')+1;out=[]
    while i<len(sys.argv) and not sys.argv[i].startswith('--'):
        out.append(sys.argv[i]);i+=1
    return out


def main():
    window=cli_value('--window');files=cli_files()
    raw=r.base.v01.load_raw(files);common_days=cs.support(raw,window)['common_raw_trading_days']
    def boot(a,b): return paired_day_bootstrap_all(a,b,common_days)
    r.paired_day_bootstrap=boot
    d.r=r
    d.main()


if __name__=='__main__':main()
