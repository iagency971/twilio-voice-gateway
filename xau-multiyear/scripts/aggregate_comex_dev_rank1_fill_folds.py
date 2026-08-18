#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import run_comex_dev_rank1_primary_models as prim
import run_comex_dev_rank1_fill_model as fill

YEARS=list(range(2011,2019))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--fold-root',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);root=Path(a.fold_root);allf=pd.read_parquet(a.features).copy();models=allf.entry_model.astype(str).unique().tolist();assert len(models)==1,models;entry_model=models[0];allf['b2_available_bool']=prim.asbool(allf.b2_available);counts={'decision_events':len(allf),'decision_sessions':int(allf.research_trading_date.nunique()),'decision_years':int(allf.year.nunique()),'filled_or_entered':int(fill.yarr(allf).sum()),'not_filled_or_entered':int(len(allf)-fill.yarr(allf).sum()),'fill_rate':float(fill.yarr(allf).mean()),'b2_available_events':int(allf.b2_available_bool.sum())};f=allf[allf.b2_available_bool].copy().reset_index(drop=True);y=fill.yarr(f);counts.update({'primary_comparison_events':len(f),'primary_sessions':int(f.research_trading_date.nunique()),'primary_fill':int(y.sum()),'primary_nonfill':int(len(f)-y.sum()),'primary_fill_rate':float(y.mean())});assert sorted(f.year.unique().tolist())==YEARS
    preds={z:np.full(len(f),np.nan) for z in ['B0','B1','B2']};aud=[];key={(str(r.event_uid),str(r.research_trading_date)):i for i,r in f[['event_uid','research_trading_date']].iterrows()}
    for z in ['B0','B1','B2']:
        for yr in YEARS:
            ps=list(root.rglob(f'pred_{z}_{yr}.parquet'));js=list(root.rglob(f'audit_{z}_{yr}.json'))
            if len(ps)!=1 or len(js)!=1:raise SystemExit(f'missing/duplicate fold {z} {yr}: pred={len(ps)} audit={len(js)}')
            q=pd.read_parquet(ps[0]);
            for r in q.itertuples(index=False):preds[z][key[(str(r.event_uid),str(r.research_trading_date))]]=float(getattr(r,f'p_{z}'))
            aud.append(json.loads(js[0].read_text()))
        if not np.isfinite(preds[z]).all():raise SystemExit(f'nonfinite/missing predictions {z}')
    pd.DataFrame(aud).to_json(out/'outer_fold_audit.json',orient='records',indent=2)
    pr=f[['event_uid','research_trading_date','year','family_stack','poststrat_weight']].copy();pr['y']=y
    for z,p in preds.items():pr[f'p_{z}']=p
    pr.to_parquet(out/'crossfit_predictions.parquet',index=False,compression='zstd')
    weights={'family_balanced_event':prim.family_balanced_weights(f),'population_event':prim.population_weights(f),'session_balanced':prim.session_weights(f)};metrics=[];losses={}
    for mode,w in weights.items():
        for z,p in preds.items():m,l=prim.metric_bundle(f,y,p,'reaction',[0,1],w);losses[(mode,z)]=l;metrics.append({'scope':'POOLED','weighting':mode,'model':z,'events':len(f),'sessions':f.research_trading_date.nunique(),**m})
    for fam,gidx in f.groupby('family_stack').groups.items():
        ii=np.array(list(gidx),int);sub=f.loc[ii];ys=y[ii]
        for mode in ['population_event','session_balanced']:
            w=prim.population_weights(sub) if mode=='population_event' else prim.session_weights(sub)
            for z,p in preds.items():m,_=prim.metric_bundle(sub,ys,p[ii],'reaction',[0,1],w);metrics.append({'scope':str(fam),'weighting':mode,'model':z,'events':len(sub),'sessions':sub.research_trading_date.nunique(),**m})
    mdf=pd.DataFrame(metrics);mdf.to_csv(out/'metrics.csv',index=False)
    annual=[]
    for yr in YEARS:
        ii=np.flatnonzero(f.year.to_numpy()==yr);sub=f.iloc[ii];w=prim.family_balanced_weights(sub);ys=y[ii]
        for z,p in preds.items():m,_=prim.metric_bundle(sub,ys,p[ii],'reaction',[0,1],w);annual.append({'year':yr,'model':z,'events':len(ii),'fill':int(ys.sum()),'nonfill':int(len(ys)-ys.sum()),**m})
    adf=pd.DataFrame(annual);adf.to_csv(out/'annual_metrics.csv',index=False);comps=[]
    for old,new in [('B0','B1'),('B1','B2')]:
        r={'comparison':f'{new}_vs_{old}'}
        for mode in weights:
            oo=mdf[(mdf.scope=='POOLED')&(mdf.weighting==mode)&(mdf.model==old)].iloc[0];nn=mdf[(mdf.scope=='POOLED')&(mdf.weighting==mode)&(mdf.model==new)].iloc[0];r[f'{mode}_logloss_improvement']=float(oo.log_loss-nn.log_loss)
        yd=[]
        for yr in YEARS:
            oo=adf[(adf.year==yr)&(adf.model==old)].iloc[0];nn=adf[(adf.year==yr)&(adf.model==new)].iloc[0];yd.append({'year':yr,'logloss_improvement':float(oo.log_loss-nn.log_loss),'fill':int(oo.fill),'nonfill':int(oo.nonfill)})
        r['year_deltas']=yd;r['positive_years']=int(sum(x['logloss_improvement']>0 for x in yd));r['cluster_bootstrap_95']=prim.bootstrap_delta(f,losses[('family_balanced_event',old)],losses[('family_balanced_event',new)],weights['family_balanced_event'],2000);r['bootstrap_excludes_zero_positive']=bool(r['cluster_bootstrap_95']['lo']>0);r['directional_gate']=bool(r['family_balanced_event_logloss_improvement']>0 and r['session_balanced_logloss_improvement']>0 and r['positive_years']>=5);comps.append(r)
    famd=[]
    for fam in sorted(f.family_stack.astype(str).unique()):
        for old,new in [('B0','B1'),('B1','B2')]:
            for mode in ['population_event','session_balanced']:
                oo=mdf[(mdf.scope==fam)&(mdf.weighting==mode)&(mdf.model==old)].iloc[0];nn=mdf[(mdf.scope==fam)&(mdf.weighting==mode)&(mdf.model==new)].iloc[0];famd.append({'family':fam,'comparison':f'{new}_vs_{old}','weighting':mode,'events':int(oo.events),'sessions':int(oo.sessions),'logloss_improvement':float(oo.log_loss-nn.log_loss)})
    pd.DataFrame(famd).to_csv(out/'family_deltas.csv',index=False);feas=fill.feasibility(f);(out/'feasibility.json').write_text(json.dumps(feas,indent=2));result={'version':'COMEX_DEV_RANK1_FILL_MODEL_RESULT_V1_PARALLEL_RECOVERY','entry_model':entry_model,'target':'fill_or_entry','counts':counts,'C_grid':prim.C_GRID,'nested_validation':'outer LOYO; C selected by identical inner LOYO on remaining years','recovery_reason':'monolithic large fill job hit GitHub timeout; 24 fold jobs preserve identical frozen specification','status':'MODELED','events':len(f),'sessions':int(f.research_trading_date.nunique()),'comparisons':comps};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
