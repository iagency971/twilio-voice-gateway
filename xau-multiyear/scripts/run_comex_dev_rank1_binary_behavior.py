#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler

C_GRID=[0.01,0.1,1.0,10.0,100.0]
YEARS=list(range(2011,2019));SEED=971
B0_CAT=['family_stack','signature','side','session','local_hour','approach_direction','approach_band']
B0_NUM=['sigma60','zone_width_sigma','constituent_count']
B1_EXCLUDE={'b1_available','b1_exact_prev_minute','b1_last_bar_age_min','b1_context_instrument_id'}
B2_EXCLUDE={'b2_available','b2_active_contract','b2_active_instrument_id','b2_p_ref','b2_session_elapsed_min'}

def asbool(s):
    if pd.api.types.is_bool_dtype(s):return s.fillna(False).astype(bool)
    return s.astype(str).str.lower().eq('true')

def columns(df):
    b1=[c for c in df.columns if c.startswith('b1_') and c not in B1_EXCLUDE]
    b2=[c for c in df.columns if c.startswith('b2_') and c not in B2_EXCLUDE and 'nshare_secondary' not in c and not c.endswith('_nvol')]
    return {'B0':B0_CAT+B0_NUM,'B1':B0_CAT+B0_NUM+b1,'B2':B0_CAT+B0_NUM+b1+b2}

def family_weights(df):
    base=pd.to_numeric(df.poststrat_weight,errors='coerce').fillna(1.0).to_numpy(float);fam=df.family_stack.astype(str).to_numpy();tot={f:float(base[fam==f].sum()) for f in np.unique(fam)};tar=float(np.mean(list(tot.values())));w=base*np.array([tar/max(tot[x],1e-12) for x in fam]);return w/max(w.mean(),1e-12)
def pop_weights(df):
    w=pd.to_numeric(df.poststrat_weight,errors='coerce').fillna(1.0).to_numpy(float);return w/max(w.mean(),1e-12)
def sess_weights(df):
    w=pd.to_numeric(df.poststrat_weight,errors='coerce').fillna(1.0).to_numpy(float);n=df.groupby('research_trading_date').event_uid.transform('size').to_numpy(float);w=w/np.maximum(n,1.0);return w/max(w.mean(),1e-12)
def clean(df,fs):
    x=df[fs].copy()
    for c in fs:
        if c in B0_CAT:x[c]=x[c].astype(object)
        else:x[c]=pd.to_numeric(x[c],errors='coerce').replace([np.inf,-np.inf],np.nan)
    return x
def prep(df,fs):
    cats=[c for c in B0_CAT if c in fs];nums=[c for c in fs if c not in cats]
    return ColumnTransformer([('cat',Pipeline([('imp',SimpleImputer(strategy='most_frequent')),('ohe',OneHotEncoder(handle_unknown='ignore'))]),cats),('num',Pipeline([('imp',SimpleImputer(strategy='median',add_indicator=True)),('scale',StandardScaler())]),nums)],remainder='drop')
def loss(y,p):
    p=np.clip(np.asarray(p,float),1e-15,1-1e-15);y=np.asarray(y,int);return -(y*np.log(p)+(1-y)*np.log(1-p))
def wmean(x,w):
    return float(np.sum(np.asarray(x)*np.asarray(w))/max(np.sum(w),1e-15))
def model(C):return LogisticRegression(C=C,penalty='l2',solver='liblinear',max_iter=500,random_state=SEED)
def choose_c(train,fs):
    scores={c:[0.0,0.0] for c in C_GRID}
    for vy in sorted(train.year.unique()):
        tr=train[train.year!=vy];va=train[train.year==vy];pp=prep(tr,fs);xt=pp.fit_transform(clean(tr,fs));xv=pp.transform(clean(va,fs));yt=tr.y.to_numpy(int);yv=va.y.to_numpy(int);wt=family_weights(tr);wv=family_weights(va)
        for C in C_GRID:
            m=model(C);m.fit(xt,yt,sample_weight=wt);p=m.predict_proba(xv)[:,list(m.classes_).index(1)];ll=loss(yv,p);scores[C][0]+=float(np.sum(ll*wv));scores[C][1]+=float(wv.sum())
    vals={C:a/max(b,1e-15) for C,(a,b) in scores.items()};return min(C_GRID,key=lambda c:(vals[c],c)),vals
def crossfit(df,fs,label):
    out=np.full(len(df),np.nan);audit=[]
    for oy in YEARS:
        tr=df[df.year!=oy];te=df[df.year==oy];C,inner=choose_c(tr,fs);pp=prep(tr,fs);xt=pp.fit_transform(clean(tr,fs));xv=pp.transform(clean(te,fs));m=model(C);m.fit(xt,tr.y.to_numpy(int),sample_weight=family_weights(tr));out[te.index.to_numpy()]=m.predict_proba(xv)[:,list(m.classes_).index(1)];audit.append({'model':label,'outer_year':oy,'selected_C':C,'inner_logloss_by_C':{str(k):v for k,v in inner.items()},'train_events':len(tr),'test_events':len(te)});print(label,oy,C,flush=True)
    return out,audit
def metric(df,p,w):
    y=df.y.to_numpy(int);l=loss(y,p);o={'log_loss':wmean(l,w),'brier':wmean((y-p)**2,w)}
    try:o['roc_auc']=float(roc_auc_score(y,p,sample_weight=w))
    except Exception:o['roc_auc']=None
    return o,l
def boot(df,old,new,w,n=2000):
    ss=np.array(sorted(df.research_trading_date.astype(str).unique()));idx={s:np.flatnonzero(df.research_trading_date.astype(str).to_numpy()==s) for s in ss};rng=np.random.default_rng(SEED);v=[]
    for _ in range(n):
        draw=rng.choice(ss,size=len(ss),replace=True);a=b=d=0.0
        for s in draw:
            ii=idx[s];ww=w[ii];d+=ww.sum();a+=np.sum(old[ii]*ww);b+=np.sum(new[ii]*ww)
        v.append(a/max(d,1e-15)-b/max(d,1e-15))
    return {'lo':float(np.quantile(v,.025)),'median':float(np.quantile(v,.5)),'hi':float(np.quantile(v,.975)),'n':n}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_parquet(a.features).copy();f=f[asbool(f.b2_available)].copy();f=f[f.behavior_v2.astype(str)!='UNRESOLVED'].copy();f['y']=np.where(f.behavior_v2.astype(str).eq('ACCEPTED_BREAK'),1,0);f=f.reset_index(drop=True);assert sorted(f.year.unique())==YEARS
    fs=columns(f);pred={};audit=[]
    for z in ['B0','B1','B2']:
        pred[z],aa=crossfit(f,fs[z],z);audit+=aa
    pd.DataFrame(audit).to_json(out/'outer_fold_audit.json',orient='records',indent=2)
    ws={'family_balanced_event':family_weights(f),'population_event':pop_weights(f),'session_balanced':sess_weights(f)};metrics=[];losses={}
    for mode,w in ws.items():
        for z,p in pred.items():m,l=metric(f,p,w);losses[(mode,z)]=l;metrics.append({'scope':'POOLED','weighting':mode,'model':z,'events':len(f),'sessions':f.research_trading_date.nunique(),**m})
    for fam,idx in f.groupby('family_stack').groups.items():
        ii=np.array(list(idx),int);sub=f.loc[ii]
        for mode in ['population_event','session_balanced']:
            w=pop_weights(sub) if mode=='population_event' else sess_weights(sub)
            for z,p in pred.items():m,_=metric(sub,p[ii],w);metrics.append({'scope':str(fam),'weighting':mode,'model':z,'events':len(sub),'sessions':sub.research_trading_date.nunique(),**m})
    pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
    annual=[]
    for y in YEARS:
        ii=np.flatnonzero(f.year.to_numpy()==y);sub=f.iloc[ii];w=family_weights(sub)
        for z,p in pred.items():m,_=metric(sub,p[ii],w);annual.append({'year':y,'model':z,'events':len(ii),**m})
    adf=pd.DataFrame(annual);adf.to_csv(out/'annual_metrics.csv',index=False)
    comps=[]
    for old,new in [('B0','B1'),('B1','B2')]:
        r={'comparison':f'{new}_vs_{old}'}
        for mode in ws:
            oo=next(x for x in metrics if x['scope']=='POOLED' and x['weighting']==mode and x['model']==old);nn=next(x for x in metrics if x['scope']=='POOLED' and x['weighting']==mode and x['model']==new);r[f'{mode}_logloss_improvement']=oo['log_loss']-nn['log_loss']
        yd=[]
        for y in YEARS:
            oo=adf[(adf.year==y)&(adf.model==old)].iloc[0];nn=adf[(adf.year==y)&(adf.model==new)].iloc[0];yd.append({'year':y,'logloss_improvement':float(oo.log_loss-nn.log_loss)})
        r['year_deltas']=yd;r['positive_years']=sum(x['logloss_improvement']>0 for x in yd);r['cluster_bootstrap_95']=boot(f,losses[('family_balanced_event',old)],losses[('family_balanced_event',new)],ws['family_balanced_event']);r['directional_gate']=bool(r['family_balanced_event_logloss_improvement']>0 and r['session_balanced_logloss_improvement']>0 and r['positive_years']>=5);comps.append(r)
    result={'version':'COMEX_DEV_RANK1_BINARY_BEHAVIOR_DIAGNOSTIC_V1','role':'SECONDARY_DIAGNOSTIC_ONLY','mapping':{'REJECT':['CLEAN_REJECTION','FAILED_AUCTION'],'ACCEPT':['ACCEPTED_BREAK'],'EXCLUDED':['UNRESOLVED']},'events':len(f),'accept_events':int(f.y.sum()),'reject_events':int((1-f.y).sum()),'sessions':int(f.research_trading_date.nunique()),'comparisons':comps,'note':'Cannot override multiclass primary behavior result.'};(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
