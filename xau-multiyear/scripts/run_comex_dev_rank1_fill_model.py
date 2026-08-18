#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import run_comex_dev_rank1_primary_models as prim

YEARS=list(range(2011,2019));C_GRID=prim.C_GRID;SEED=971

def yarr(df):
    s=df.fill_or_entry
    if pd.api.types.is_bool_dtype(s):return s.fillna(False).astype(int).to_numpy()
    return s.astype(str).str.lower().eq('true').astype(int).to_numpy()

def feasibility(df):
    out={'overall_classes':sorted(np.unique(yarr(df)).astype(int).tolist()),'outer':[],'identifiable':True}
    for oy in YEARS:
        tr=df[df.year!=oy];te=df[df.year==oy];r={'outer_year':oy,'train_classes':sorted(np.unique(yarr(tr)).astype(int).tolist()),'test_classes':sorted(np.unique(yarr(te)).astype(int).tolist()),'train_events':len(tr),'test_events':len(te),'inner':[]}
        if len(r['train_classes'])<2:out['identifiable']=False
        for vy in sorted(tr.year.unique()):
            inn=tr[tr.year!=vy];cls=sorted(np.unique(yarr(inn)).astype(int).tolist());r['inner'].append({'validation_year':int(vy),'inner_train_classes':cls,'inner_train_events':len(inn)})
            if len(cls)<2:out['identifiable']=False
        out['outer'].append(r)
    return out

def choose_c(train,features):
    scores={c:[0.0,0.0] for c in C_GRID}
    for vy in sorted(train.year.unique()):
        tr=train[train.year!=vy];va=train[train.year==vy];prep,_,_=prim.make_preprocessor(tr,features);xt=prep.fit_transform(prim.clean_X(tr,features));xv=prep.transform(prim.clean_X(va,features));yt=yarr(tr);yv=yarr(va);wt=prim.family_balanced_weights(tr);wv=prim.family_balanced_weights(va)
        for C in C_GRID:
            m=prim.model_for('reaction',C);m.fit(xt,yt,sample_weight=wt);raw=m.predict_proba(xv);j=list(m.classes_).index(1);p=raw[:,j];loss=prim.event_loss(yv,p,'reaction',[0,1]);scores[C][0]+=float(np.sum(loss*wv));scores[C][1]+=float(np.sum(wv))
    vals={C:a/max(b,1e-15) for C,(a,b) in scores.items()};best=min(C_GRID,key=lambda c:(vals[c],c));return best,vals

def nested(df,features,label):
    p=np.full(len(df),np.nan);audit=[]
    for oy in YEARS:
        tr=df[df.year!=oy];te=df[df.year==oy];C,inner=choose_c(tr,features);prep,_,_=prim.make_preprocessor(tr,features);xt=prep.fit_transform(prim.clean_X(tr,features));xv=prep.transform(prim.clean_X(te,features));m=prim.model_for('reaction',C);m.fit(xt,yarr(tr),sample_weight=prim.family_balanced_weights(tr));raw=m.predict_proba(xv);j=list(m.classes_).index(1);p[te.index.to_numpy()]=raw[:,j];audit.append({'model':label,'outer_year':oy,'selected_C':C,'inner_logloss_by_C':{str(k):v for k,v in inner.items()},'train_events':len(tr),'test_events':len(te),'train_fill':int(yarr(tr).sum()),'test_fill':int(yarr(te).sum())});print(label,oy,C,flush=True)
    return p,audit

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    allf=pd.read_parquet(a.features).copy();models=allf.entry_model.astype(str).unique().tolist();assert len(models)==1,models;model=models[0]
    allf['b2_available_bool']=prim.asbool(allf.b2_available);all_counts={'decision_events':len(allf),'decision_sessions':int(allf.research_trading_date.nunique()),'decision_years':int(allf.year.nunique()),'filled_or_entered':int(yarr(allf).sum()),'not_filled_or_entered':int(len(allf)-yarr(allf).sum()),'fill_rate':float(yarr(allf).mean()),'b2_available_events':int(allf.b2_available_bool.sum())}
    f=allf[allf.b2_available_bool].copy().reset_index(drop=True);y=yarr(f);all_counts.update({'primary_comparison_events':len(f),'primary_sessions':int(f.research_trading_date.nunique()),'primary_fill':int(y.sum()),'primary_nonfill':int(len(f)-y.sum()),'primary_fill_rate':float(y.mean()) if len(f) else None})
    class_rows=[]
    for yr in sorted(allf.year.unique()):
        g=allf[allf.year==yr];gg=g[prim.asbool(g.b2_available)];class_rows.append({'scope':'year','key':str(yr),'decision_events':len(g),'fill':int(yarr(g).sum()),'nonfill':int(len(g)-yarr(g).sum()),'b2_events':len(gg),'b2_fill':int(yarr(gg).sum()),'b2_nonfill':int(len(gg)-yarr(gg).sum()),'sessions':int(g.research_trading_date.nunique())})
    for fam,g in allf.groupby('family_stack'):
        gg=g[prim.asbool(g.b2_available)];class_rows.append({'scope':'family','key':str(fam),'decision_events':len(g),'fill':int(yarr(g).sum()),'nonfill':int(len(g)-yarr(g).sum()),'b2_events':len(gg),'b2_fill':int(yarr(gg).sum()),'b2_nonfill':int(len(gg)-yarr(gg).sum()),'sessions':int(g.research_trading_date.nunique())})
    pd.DataFrame(class_rows).to_csv(out/'class_counts.csv',index=False)
    feas=feasibility(f) if len(f) else {'identifiable':False,'reason':'no B2 rows'};(out/'feasibility.json').write_text(json.dumps(feas,indent=2))
    base={'version':'COMEX_DEV_RANK1_FILL_MODEL_RESULT_V1','entry_model':model,'target':'fill_or_entry','counts':all_counts,'C_grid':C_GRID,'nested_validation':'outer LOYO; C selected by inner LOYO on remaining years','freeze':'COMEX_DEV_RANK1_FILL_MODEL_FREEZE_v1.md'}
    if len(f)==0 or len(np.unique(y))<2 or not feas.get('identifiable',False):
        base.update({'status':'NON_IDENTIFIABLE','comparisons':[],'note':'Frozen nested procedure cannot be fit with both outcome classes in every required training split. Descriptive counts only.'});(out/'result.json').write_text(json.dumps(base,indent=2));pd.DataFrame().to_csv(out/'metrics.csv',index=False);pd.DataFrame().to_csv(out/'annual_metrics.csv',index=False);pd.DataFrame().to_csv(out/'family_deltas.csv',index=False);pd.DataFrame().to_json(out/'outer_fold_audit.json',orient='records');print(json.dumps(base,indent=2));return
    cols,_,_=prim.primary_columns(f);pred={};audit=[]
    for z in ['B0','B1','B2']:
        pred[z],aa=nested(f,cols[z],z);audit+=aa
    pd.DataFrame(audit).to_json(out/'outer_fold_audit.json',orient='records',indent=2)
    weights={'family_balanced_event':prim.family_balanced_weights(f),'population_event':prim.population_weights(f),'session_balanced':prim.session_weights(f)};metrics=[];losses={}
    for mode,w in weights.items():
        for z,p in pred.items():m,l=prim.metric_bundle(f,y,p,'reaction',[0,1],w);losses[(mode,z)]=l;metrics.append({'scope':'POOLED','weighting':mode,'model':z,'events':len(f),'sessions':f.research_trading_date.nunique(),**m})
    for fam,gidx in f.groupby('family_stack').groups.items():
        ii=np.array(list(gidx),int);sub=f.loc[ii];ys=y[ii]
        for mode in ['population_event','session_balanced']:
            w=prim.population_weights(sub) if mode=='population_event' else prim.session_weights(sub)
            for z,p in pred.items():m,_=prim.metric_bundle(sub,ys,p[ii],'reaction',[0,1],w);metrics.append({'scope':str(fam),'weighting':mode,'model':z,'events':len(sub),'sessions':sub.research_trading_date.nunique(),**m})
    mdf=pd.DataFrame(metrics);mdf.to_csv(out/'metrics.csv',index=False)
    annual=[]
    for yr in YEARS:
        ii=np.flatnonzero(f.year.to_numpy()==yr);sub=f.iloc[ii];w=prim.family_balanced_weights(sub);ys=y[ii]
        for z,p in pred.items():m,_=prim.metric_bundle(sub,ys,p[ii],'reaction',[0,1],w);annual.append({'year':yr,'model':z,'events':len(ii),'fill':int(ys.sum()),'nonfill':int(len(ys)-ys.sum()),**m})
    adf=pd.DataFrame(annual);adf.to_csv(out/'annual_metrics.csv',index=False)
    comps=[]
    for old,new in [('B0','B1'),('B1','B2')]:
        r={'comparison':f'{new}_vs_{old}'}
        for mode in weights:
            oo=next(x for x in metrics if x['scope']=='POOLED' and x['weighting']==mode and x['model']==old);nn=next(x for x in metrics if x['scope']=='POOLED' and x['weighting']==mode and x['model']==new);r[f'{mode}_logloss_improvement']=float(oo['log_loss']-nn['log_loss'])
        yd=[]
        for yr in YEARS:
            oo=adf[(adf.year==yr)&(adf.model==old)].iloc[0];nn=adf[(adf.year==yr)&(adf.model==new)].iloc[0];yd.append({'year':yr,'logloss_improvement':float(oo.log_loss-nn.log_loss),'fill':int(oo.fill),'nonfill':int(oo.nonfill)})
        r['year_deltas']=yd;r['positive_years']=int(sum(x['logloss_improvement']>0 for x in yd));r['cluster_bootstrap_95']=prim.bootstrap_delta(f,losses[('family_balanced_event',old)],losses[('family_balanced_event',new)],weights['family_balanced_event'],2000);r['bootstrap_excludes_zero_positive']=bool(r['cluster_bootstrap_95']['lo']>0);r['directional_gate']=bool(r['family_balanced_event_logloss_improvement']>0 and r['session_balanced_logloss_improvement']>0 and r['positive_years']>=5);comps.append(r)
    famd=[]
    for fam in sorted(f.family_stack.astype(str).unique()):
        for old,new in [('B0','B1'),('B1','B2')]:
            for mode in ['population_event','session_balanced']:
                oo=mdf[(mdf.scope==fam)&(mdf.weighting==mode)&(mdf.model==old)].iloc[0];nn=mdf[(mdf.scope==fam)&(mdf.weighting==mode)&(mdf.model==new)].iloc[0];famd.append({'family':fam,'comparison':f'{new}_vs_{old}','weighting':mode,'events':int(oo.events),'sessions':int(oo.sessions),'logloss_improvement':float(oo.log_loss-nn.log_loss)})
    pd.DataFrame(famd).to_csv(out/'family_deltas.csv',index=False)
    base.update({'status':'MODELED','events':len(f),'sessions':int(f.research_trading_date.nunique()),'comparisons':comps});(out/'result.json').write_text(json.dumps(base,indent=2));print(json.dumps(base,indent=2))
if __name__=='__main__':main()
