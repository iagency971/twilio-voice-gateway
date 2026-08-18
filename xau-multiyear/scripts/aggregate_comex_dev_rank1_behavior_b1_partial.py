#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import run_comex_dev_rank1_primary_models as prim
CLASSES=['CLEAN_REJECTION','FAILED_AUCTION','ACCEPTED_BREAK','UNRESOLVED'];YEARS=list(range(2011,2019))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--fold-root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);root=Path(a.fold_root)
    f=pd.read_parquet(a.features).copy();f=f[prim.asbool(f.b2_available)].copy().reset_index(drop=True);y=prim.target_array(f,'behavior');preds={z:np.full((len(f),len(CLASSES)),np.nan) for z in ['B0','B1']};key={(str(r.event_uid),str(r.research_trading_date)):i for i,r in f[['event_uid','research_trading_date']].iterrows()}
    audits=[]
    for z in ['B0','B1']:
        for yr in YEARS:
            ps=list(root.rglob(f'pred_{z}_{yr}.parquet'));js=list(root.rglob(f'audit_{z}_{yr}.json'))
            if len(ps)!=1 or len(js)!=1:raise SystemExit(f'missing fold {z} {yr}: {len(ps)}/{len(js)}')
            q=pd.read_parquet(ps[0]);audits.append(json.loads(js[0].read_text()))
            for r in q.itertuples(index=False):
                i=key[(str(r.event_uid),str(r.research_trading_date))]
                for j,c in enumerate(CLASSES):preds[z][i,j]=float(getattr(r,f'p_{z}_{c}'))
        assert np.isfinite(preds[z]).all()
    weights={'family_balanced_event':prim.family_balanced_weights(f),'population_event':prim.population_weights(f),'session_balanced':prim.session_weights(f)};metrics=[];losses={}
    for mode,w in weights.items():
        for z,p in preds.items():m,l=prim.metric_bundle(f,y,p,'behavior',CLASSES,w);losses[(mode,z)]=l;metrics.append({'scope':'POOLED','weighting':mode,'model':z,'events':len(f),'sessions':f.research_trading_date.nunique(),**m})
    annual=[]
    for yr in YEARS:
        ii=np.flatnonzero(f.year.to_numpy()==yr);sub=f.iloc[ii];w=prim.family_balanced_weights(sub);ys=y[ii]
        for z,p in preds.items():m,_=prim.metric_bundle(sub,ys,p[ii,:],'behavior',CLASSES,w);annual.append({'year':yr,'model':z,'events':len(ii),**m})
    adf=pd.DataFrame(annual);adf.to_csv(out/'annual_metrics.csv',index=False);pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False);pd.DataFrame(audits).to_json(out/'outer_fold_audit.json',orient='records',indent=2)
    old='B0';new='B1';r={'comparison':'B1_vs_B0'}
    for mode in weights:
        oo=next(x for x in metrics if x['weighting']==mode and x['model']==old);nn=next(x for x in metrics if x['weighting']==mode and x['model']==new);r[f'{mode}_logloss_improvement']=float(oo['log_loss']-nn['log_loss'])
    yd=[]
    for yr in YEARS:
        oo=adf[(adf.year==yr)&(adf.model==old)].iloc[0];nn=adf[(adf.year==yr)&(adf.model==new)].iloc[0];yd.append({'year':yr,'logloss_improvement':float(oo.log_loss-nn.log_loss)})
    r['year_deltas']=yd;r['positive_years']=int(sum(x['logloss_improvement']>0 for x in yd));r['cluster_bootstrap_95']=prim.bootstrap_delta(f,losses[('family_balanced_event','B0')],losses[('family_balanced_event','B1')],weights['family_balanced_event'],2000);r['directional_gate']=bool(r['family_balanced_event_logloss_improvement']>0 and r['session_balanced_logloss_improvement']>0 and r['positive_years']>=5)
    result={'version':'COMEX_DEV_RANK1_BEHAVIOR_B1_INTERMEDIATE_FREEZE_V1','role':'INTERMEDIATE_PRIMARY_COMPONENT','target':'behavior_v2 multiclass','events':len(f),'sessions':int(f.research_trading_date.nunique()),'comparison':r,'note':'All 8 B0 and all 8 B1 outer folds were complete before this aggregation. B2 was still running; this file freezes only B1 versus B0 and cannot prejudge B2.'};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
