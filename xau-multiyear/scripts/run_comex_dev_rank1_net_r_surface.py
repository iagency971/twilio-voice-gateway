#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
import run_comex_dev_rank1_primary_models as prim

YEARS=list(range(2011,2019));C_GRID=prim.C_GRID;SEED=971

def wm(x,w):return prim.weighted_mean(np.asarray(x,float),np.asarray(w,float))
def pf(x,w=None):
    a=np.asarray(x,float);ww=np.ones(len(a),float) if w is None else np.asarray(w,float);good=np.isfinite(a)&np.isfinite(ww)&(ww>=0);a=a[good];ww=ww[good];pos=float(np.sum(a[a>0]*ww[a>0]));neg=float(-np.sum(a[a<0]*ww[a<0]));return float(pos/neg) if neg>0 else (float('inf') if pos>0 else None)
def losses(y,p):return (np.asarray(y,float)-np.asarray(p,float))**2

def choose_c(train,features):
    scores={c:[0.0,0.0] for c in C_GRID}
    for vy in sorted(train.year.unique()):
        tr=train[train.year!=vy];va=train[train.year==vy];prep,_,_=prim.make_preprocessor(tr,features);xt=prep.fit_transform(prim.clean_X(tr,features));xv=prep.transform(prim.clean_X(va,features));yt=tr.net_R.to_numpy(float);yv=va.net_R.to_numpy(float);wt=prim.family_balanced_weights(tr);wv=prim.family_balanced_weights(va)
        for C in C_GRID:
            m=Ridge(alpha=1.0/float(C));m.fit(xt,yt,sample_weight=wt);pr=m.predict(xv);l=losses(yv,pr);scores[C][0]+=float(np.sum(l*wv));scores[C][1]+=float(np.sum(wv))
    vals={C:a/max(b,1e-15) for C,(a,b) in scores.items()};best=min(C_GRID,key=lambda c:(vals[c],c));return best,vals

def nested(df,features,label):
    p=np.full(len(df),np.nan);audit=[]
    for oy in YEARS:
        tr=df[df.year!=oy];te=df[df.year==oy];C,inner=choose_c(tr,features);prep,_,_=prim.make_preprocessor(tr,features);xt=prep.fit_transform(prim.clean_X(tr,features));xv=prep.transform(prim.clean_X(te,features));m=Ridge(alpha=1.0/float(C));m.fit(xt,tr.net_R.to_numpy(float),sample_weight=prim.family_balanced_weights(tr));p[te.index.to_numpy()]=m.predict(xv);audit.append({'model':label,'outer_year':oy,'selected_C':C,'selected_alpha':1.0/float(C),'inner_mse_by_C':{str(k):v for k,v in inner.items()},'train_events':len(tr),'test_events':len(te)});print(label,oy,C,flush=True)
    return p,audit

def bundle(y,p,w):
    e=np.asarray(y,float)-np.asarray(p,float);return {'mse':wm(e*e,w),'mae':wm(np.abs(e),w)},e*e

def bootstrap_delta(df,loss_old,loss_new,w,n=2000):
    sessions=np.array(sorted(df.research_trading_date.astype(str).unique()));arr=df.research_trading_date.astype(str).to_numpy();idx={s:np.flatnonzero(arr==s) for s in sessions};rng=np.random.default_rng(SEED);vals=[]
    for _ in range(n):
        draw=rng.choice(sessions,size=len(sessions),replace=True);ao=an=den=0.0
        for s in draw:
            ii=idx[s];ww=w[ii];den+=float(ww.sum());ao+=float(np.sum(loss_old[ii]*ww));an+=float(np.sum(loss_new[ii]*ww))
        vals.append(ao/max(den,1e-15)-an/max(den,1e-15))
    return {'lo':float(np.quantile(vals,.025)),'median':float(np.quantile(vals,.5)),'hi':float(np.quantile(vals,.975)),'n':n}

def economic(df):
    rows=[]
    for mode,w in [('family_balanced_event',prim.family_balanced_weights(df)),('population_event',prim.population_weights(df)),('session_balanced',prim.session_weights(df))]:rows.append({'scope':'POOLED','weighting':mode,'events':len(df),'sessions':int(df.research_trading_date.nunique()),'avg_net_R':wm(df.net_R,w),'pf_net':pf(df.net_R,w),'sum_weighted_net_R':float(np.sum(df.net_R.to_numpy(float)*w))})
    for yr,g in df.groupby('year'):
        w=prim.family_balanced_weights(g);rows.append({'scope':'YEAR','key':int(yr),'weighting':'family_balanced_event','events':len(g),'sessions':int(g.research_trading_date.nunique()),'avg_net_R':wm(g.net_R,w),'pf_net':pf(g.net_R,w),'sum_weighted_net_R':float(np.sum(g.net_R.to_numpy(float)*w))})
    return pd.DataFrame(rows)

def analyze_cell(df,entry_model,risk_rule,target_r,scenario,out):
    q=df[(df.entry_model==entry_model)&(df.risk_rule==risk_rule)&(np.isclose(df.target_r.astype(float),float(target_r)))&(df.scenario==scenario)].copy();q=q[prim.asbool(q.b2_available)].reset_index(drop=True);result={'entry_model':entry_model,'risk_rule':risk_rule,'target_r':float(target_r),'scenario':scenario,'events':len(q),'sessions':int(q.research_trading_date.nunique()),'years':sorted(int(x) for x in q.year.unique())}
    if sorted(q.year.unique().tolist())!=YEARS or len(q)<20:
        result.update({'status':'INCONCLUSIVE','comparisons':[],'reason':'insufficient temporal coverage or events'});return result
    cols,_,_=prim.primary_columns(q);pred={};audit=[]
    for z in ['B0','B1','B2']:
        pred[z],aa=nested(q,cols[z],z);audit+=aa
    pd.DataFrame(audit).to_json(out/f'audit_rr{float(target_r):.2f}.json',orient='records',indent=2)
    weights={'family_balanced_event':prim.family_balanced_weights(q),'population_event':prim.population_weights(q),'session_balanced':prim.session_weights(q)};metrics=[];ls={};y=q.net_R.to_numpy(float)
    for mode,w in weights.items():
        for z,p in pred.items():m,l=bundle(y,p,w);ls[(mode,z)]=l;metrics.append({'scope':'POOLED','weighting':mode,'model':z,'events':len(q),'sessions':q.research_trading_date.nunique(),**m})
    for fam,gidx in q.groupby('family_stack').groups.items():
        ii=np.array(list(gidx),int);sub=q.loc[ii];ys=y[ii]
        for mode in ['population_event','session_balanced']:
            w=prim.population_weights(sub) if mode=='population_event' else prim.session_weights(sub)
            for z,p in pred.items():m,_=bundle(ys,p[ii],w);metrics.append({'scope':str(fam),'weighting':mode,'model':z,'events':len(sub),'sessions':sub.research_trading_date.nunique(),**m})
    mdf=pd.DataFrame(metrics);mdf.to_csv(out/f'metrics_rr{float(target_r):.2f}.csv',index=False)
    annual=[]
    for yr in YEARS:
        ii=np.flatnonzero(q.year.to_numpy()==yr);sub=q.iloc[ii];w=prim.family_balanced_weights(sub);ys=y[ii]
        for z,p in pred.items():m,_=bundle(ys,p[ii],w);annual.append({'year':yr,'model':z,'events':len(ii),**m})
    adf=pd.DataFrame(annual);adf.to_csv(out/f'annual_rr{float(target_r):.2f}.csv',index=False)
    comps=[]
    for old,new in [('B0','B1'),('B1','B2')]:
        r={'comparison':f'{new}_vs_{old}'}
        for mode in weights:
            oo=mdf[(mdf.scope=='POOLED')&(mdf.weighting==mode)&(mdf.model==old)].iloc[0];nn=mdf[(mdf.scope=='POOLED')&(mdf.weighting==mode)&(mdf.model==new)].iloc[0];r[f'{mode}_mse_improvement']=float(oo.mse-nn.mse)
        yd=[]
        for yr in YEARS:
            oo=adf[(adf.year==yr)&(adf.model==old)].iloc[0];nn=adf[(adf.year==yr)&(adf.model==new)].iloc[0];yd.append({'year':yr,'mse_improvement':float(oo.mse-nn.mse)})
        r['year_deltas']=yd;r['positive_years']=int(sum(x['mse_improvement']>0 for x in yd));r['cluster_bootstrap_95']=bootstrap_delta(q,ls[('family_balanced_event',old)],ls[('family_balanced_event',new)],weights['family_balanced_event'],2000);r['directional_gate']=bool(r['family_balanced_event_mse_improvement']>0 and r['session_balanced_mse_improvement']>0 and r['positive_years']>=5);comps.append(r)
    result.update({'status':'MODELED','comparisons':comps});return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--outcomes',required=True);ap.add_argument('--entry-model',required=True);ap.add_argument('--risk-rule',required=True);ap.add_argument('--scenario',default='S11_C6_PRIMARY');ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);f=pd.read_parquet(a.features);o=pd.read_parquet(a.outcomes);o=o[(o.entry_model==a.entry_model)&(o.risk_rule==a.risk_rule)&(o.scenario==a.scenario)].copy();keep=[c for c in o.columns if c not in f.columns or c in ['event_uid']];x=f.merge(o[keep],on='event_uid',how='inner',validate='one_to_many');x['net_R']=pd.to_numeric(x.net_R,errors='coerce');x=x[np.isfinite(x.net_R)].copy();assert set(x.entry_model.astype(str).unique())=={a.entry_model};eco=[];results=[]
    for rr in sorted(float(z) for z in x.target_r.unique()):
        g=x[np.isclose(x.target_r.astype(float),rr)].copy();e=economic(g);e['target_r']=rr;eco.append(e);results.append(analyze_cell(x,a.entry_model,a.risk_rule,rr,a.scenario,out))
    pd.concat(eco,ignore_index=True).to_csv(out/'economic_summary.csv',index=False);summary={'version':'COMEX_DEV_RANK1_NET_R_SURFACE_RESULT_V1','entry_model':a.entry_model,'risk_rule':a.risk_rule,'scenario':a.scenario,'C_grid':C_GRID,'alpha_mapping':'alpha=1/C','freeze':'COMEX_DEV_RANK1_NET_R_SURFACE_FREEZE_v1.md','trade_selection_threshold_used':False,'results':results};(out/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
