#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--matching',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def main():
    a=args()
    m=pd.read_csv(a.matching,compression='infer',float_precision='round_trip')
    x=m.donor_zone_width_v.to_numpy(float)
    y=m.recipient_transplanted_zone_width_v.to_numpy(float)
    d=np.abs(x-y)
    spacing=np.maximum(np.abs(np.spacing(x)),np.abs(np.spacing(y)))
    spacing=np.maximum(spacing,np.finfo(float).tiny)
    ulp=d/spacing
    thresholds=[0.0,1e-15,1e-14,1e-13,1e-12,2e-12,5e-12,1e-11,1e-10]
    counts={format(t,'.1e'):int(np.sum(d>t)) for t in thresholds}
    nz=np.flatnonzero(d>0)
    worst=np.argsort(d)[-20:][::-1]
    examples=[]
    for i in worst:
        if d[i]==0:continue
        r=m.iloc[int(i)]
        examples.append({
            'row_index':int(i),
            'donor_episode_id':str(r.donor_episode_id),
            'control_rank':int(r.control_rank),
            'recipient_session_date_ny':str(r.recipient_session_date_ny),
            'donor_zone_width_v':float(x[i]),
            'recipient_transplanted_zone_width_v':float(y[i]),
            'absolute_delta':float(d[i]),
            'relative_delta':float(d[i]/max(abs(x[i]),abs(y[i]),np.finfo(float).tiny)),
            'delta_in_max_local_ulp':float(ulp[i]),
        })
    q=[0,.5,.9,.99,.999,1.0]
    out={
        'status':'R4_REP_WIDTH_FLOAT_DIAGNOSTIC_COMPLETE',
        'future_price_outcomes_used':False,
        'rows':int(len(m)),
        'nonzero_delta_rows':int(len(nz)),
        'count_abs_delta_gt':counts,
        'max_absolute_delta':float(d.max()) if len(d) else None,
        'max_relative_delta':float(np.max(d/np.maximum(np.maximum(np.abs(x),np.abs(y)),np.finfo(float).tiny))) if len(d) else None,
        'max_delta_in_local_ulp':float(ulp.max()) if len(ulp) else None,
        'delta_quantiles':{str(z):float(np.quantile(d,z)) for z in q} if len(d) else {},
        'ulp_quantiles_nonzero':{str(z):float(np.quantile(ulp[nz],z)) for z in q} if len(nz) else {},
        'allclose_atol_2e_12':bool(np.allclose(x,y,rtol=0,atol=2e-12)),
        'worst_examples':examples,
        'interpretation_guard':'DIAGNOSTIC_ONLY_NO_R4_DESIGN_CHANGE_NO_OUTCOME_AUTHORIZATION'
    }
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))


if __name__=='__main__':
    main()
