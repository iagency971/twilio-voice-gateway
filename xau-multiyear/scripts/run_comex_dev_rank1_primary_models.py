#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

C_GRID=[0.01,0.1,1.0,10.0,100.0]
YEARS=list(range(2011,2019))
B0_CAT=['family_stack','signature','side','session','local_hour','approach_direction','approach_band']
B0_NUM=['sigma60','zone_width_sigma','constituent_count']
B1_EXCLUDE={'b1_available','b1_exact_prev_minute','b1_last_bar_age_min','b1_context_instrument_id'}
B2_EXCLUDE={'b2_available','b2_active_contract','b2_active_instrument_id','b2_p_ref','b2_session_elapsed_min'}
SEED=971


def asbool(s):
    if pd.api.types.is_bool_dtype(s):return s.fillna(False).astype(bool)
    return s.astype(str).str.lower().eq('true')


def primary_columns(df):
    b1=[c for c in df.columns if c.startswith('b1_') and c not in B1_EXCLUDE]
    b2=[c for c in df.columns if c.startswith('b2_') and c not in B2_EXCLUDE and 'nshare_secondary' not in c and not c.endswith('_nvol')]
    return {'B0':B0_CAT+B0_NUM,'B1':B0_CAT+B0_NUM+b1,'B2':B0_CAT+B0_NUM+b1+b2},b1,b2


def family_balanced_weights(df):
    base=pd.to_numeric(df.poststrat_weight,errors='coerce').fillna(1.0).to_numpy(float)
    fam=df.family_stack.astype(str).to_numpy()
    totals={f:float(base[fam==f].sum()) for f in np.unique(fam)}
    target=float(np.mean(list(totals.values())))
    mult=np.array([target/max(totals[x],1e-12) for x in fam],float)
    w=base*mult
    return w/max(float(np.mean(w)),1e-12)


def population_weights(df):
    w=pd.to_numeric(df.poststrat_weight,errors='coerce').fillna(1.0).to_numpy(float)
    return w/max(float(np.mean(w)),1e-12)


def session_weights(df):
    base=pd.to_numeric(df.poststrat_weight,errors='coerce').fillna(1.0).to_numpy(float)
    n=df.groupby('research_trading_date').event_uid.transform('size').to_numpy(float)
    w=base/np.maximum(n,1.0)
    return w/max(float(np.mean(w)),1e-12)


def make_preprocessor(df,features):
    cats=[c for c in B0_CAT if c in features]
    nums=[c for c in features if c not in cats]
    cat=Pipeline([('imp',SimpleImputer(strategy='most_frequent')),('ohe',OneHotEncoder(handle_unknown='ignore'))])
    num=Pipeline([('imp',SimpleImputer(strategy='median',add_indicator=True)),('scale',StandardScaler())])
    return ColumnTransformer([('cat',cat,cats),('num',num,nums)],remainder='drop'),cats,nums


def clean_X(df,features):
    x=df[features].copy()
    for c in features:
        if c not in B0_CAT:
            x[c]=pd.to_numeric(x[c],errors='coerce').replace([np.inf,-np.inf],np.nan)
        else:x[c]=x[c].astype(object)
    return x


def model_for(target,C):
    if target=='reaction':
        return LogisticRegression(C=C,penalty='l2',solver='liblinear',max_iter=500,random_state=SEED)
    return LogisticRegression(C=C,penalty='l2',solver='lbfgs',max_iter=500,random_state=SEED)


def align_proba(model,p,classes):
    out=np.full((len(p),len(classes)),1e-15,float)
    pos={str(c):i for i,c in enumerate(classes)}
    for j,c in enumerate(model.classes_):
        if str(c) in pos:out[:,pos[str(c)]]=p[:,j]
    out=np.clip(out,1e-15,1.0);out/=out.sum(axis=1,keepdims=True)
    return out


def event_loss(y,p,target,classes):
    if target=='reaction':
        yy=np.asarray(y,int);pp=np.clip(np.asarray(p,float),1e-15,1-1e-15)
        return -(yy*np.log(pp)+(1-yy)*np.log(1-pp))
    yy=np.asarray(y,str);pos={str(c):i for i,c in enumerate(classes)}
    idx=np.array([pos[str(v)] for v in yy],int);return -np.log(np.clip(p[np.arange(len(p)),idx],1e-15,1.0))


def weighted_mean(x,w):
    x=np.asarray(x,float);w=np.asarray(w,float);good=np.isfinite(x)&np.isfinite(w)&(w>=0)
    return float(np.sum(x[good]*w[good])/max(np.sum(w[good]),1e-15))


def choose_c(train,features,target,classes):
    scores={c:[0.0,0.0] for c in C_GRID}
    for vy in sorted(train.year.unique()):
        tr=train[train.year!=vy];va=train[train.year==vy]
        prep,_,_=make_preprocessor(tr,features);xt=prep.fit_transform(clean_X(tr,features));xv=prep.transform(clean_X(va,features))
        yt=target_array(tr,target);yv=target_array(va,target);wt=family_balanced_weights(tr);wv=family_balanced_weights(va)
        for C in C_GRID:
            m=model_for(target,C);m.fit(xt,yt,sample_weight=wt);raw=m.predict_proba(xv)
            if target=='reaction':
                # model.classes_ may be [False,True] or [0,1]
                j=list(m.classes_).index(1) if 1 in list(m.classes_) else list(m.classes_).index(True);p=raw[:,j];loss=event_loss(yv,p,target,classes)
            else:p=align_proba(m,raw,classes);loss=event_loss(yv,p,target,classes)
            scores[C][0]+=float(np.sum(loss*wv));scores[C][1]+=float(np.sum(wv))
    vals={C:a/max(b,1e-15) for C,(a,b) in scores.items()}
    best=min(C_GRID,key=lambda c:(vals[c],c))
    return best,vals


def target_array(df,target):
    return asbool(df.reaction_0_5sigma).astype(int).to_numpy() if target=='reaction' else df.behavior_v2.astype(str).to_numpy()


def nested_predictions(df,features,target,classes,label):
    pred=np.full(len(df),np.nan) if target=='reaction' else np.full((len(df),len(classes)),np.nan)
    audit=[]
    for oy in YEARS:
        train=df[df.year!=oy];test=df[df.year==oy]
        C,inner=choose_c(train,features,target,classes)
        prep,_,_=make_preprocessor(train,features);xt=prep.fit_transform(clean_X(train,features));xv=prep.transform(clean_X(test,features));yt=target_array(train,target);wt=family_balanced_weights(train);m=model_for(target,C);m.fit(xt,yt,sample_weight=wt);raw=m.predict_proba(xv)
        if target=='reaction':
            j=list(m.classes_).index(1) if 1 in list(m.classes_) else list(m.classes_).index(True);pred[test.index.to_numpy()]=raw[:,j]
        else:pred[test.index.to_numpy(),:]=align_proba(m,raw,classes)
        audit.append({'model':label,'outer_year':oy,'selected_C':C,'inner_logloss_by_C':{str(k):v for k,v in inner.items()},'train_events':len(train),'test_events':len(test)})
        print(f'{target} {label} outer={oy} C={C} train={len(train)} test={len(test)}',flush=True)
    return pred,audit


def metric_bundle(df,y,p,target,classes,w):
    loss=event_loss(y,p,target,classes);out={'log_loss':weighted_mean(loss,w)}
    if target=='reaction':
        yy=np.asarray(y,int);pp=np.asarray(p,float);out['brier']=weighted_mean((yy-pp)**2,w)
        try:out['roc_auc']=float(roc_auc_score(yy,pp,sample_weight=w))
        except Exception:out['roc_auc']=None
        good=np.isfinite(pp)&(pp>0)&(pp<1)
        try:
            z=np.log(np.clip(pp[good],1e-9,1-1e-9)/(1-np.clip(pp[good],1e-9,1-1e-9))).reshape(-1,1);cal=LogisticRegression(penalty=None,solver='lbfgs',max_iter=300);cal.fit(z,yy[good],sample_weight=np.asarray(w)[good]);out['calibration_intercept']=float(cal.intercept_[0]);out['calibration_slope']=float(cal.coef_[0,0])
        except Exception:out['calibration_intercept']=out['calibration_slope']=None
    else:
        yy=np.asarray(y,str);one=np.zeros_like(p);pos={str(c):i for i,c in enumerate(classes)}
        for i,v in enumerate(yy):one[i,pos[str(v)]]=1.0
        b=np.mean((one-p)**2,axis=1);out['macro_brier']=weighted_mean(b,w);out['accuracy']=weighted_mean((np.array(classes)[np.argmax(p,axis=1)]==yy).astype(float),w)
    return out,loss


def bootstrap_delta(df,loss_old,loss_new,w,n=2000):
    sessions=np.array(sorted(df.research_trading_date.astype(str).unique()));idxs={s:np.flatnonzero(df.research_trading_date.astype(str).to_numpy()==s) for s in sessions};rng=np.random.default_rng(SEED);vals=[]
    for _ in range(n):
        draw=rng.choice(sessions,size=len(sessions),replace=True);no=nn=den=0.0
        for s in draw:
            ii=idxs[s];ww=w[ii];den+=float(ww.sum());no+=float(np.sum(loss_old[ii]*ww));nn+=float(np.sum(loss_new[ii]*ww))
        vals.append(no/max(den,1e-15)-nn/max(den,1e-15))
    return {'lo':float(np.quantile(vals,.025)),'median':float(np.quantile(vals,.5)),'hi':float(np.quantile(vals,.975)),'n':n}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--target',choices=['reaction','behavior'],required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_parquet(a.features).copy();f=f[asbool(f.b2_available)].copy().reset_index(drop=True);assert len(f)==30525,len(f);assert sorted(f.year.unique().tolist())==YEARS
    cols,b1,b2=primary_columns(f);classes=[0,1] if a.target=='reaction' else ['CLEAN_REJECTION','FAILED_AUCTION','ACCEPTED_BREAK','UNRESOLVED'];y=target_array(f,a.target)
    preds={};aud=[]
    for label in ['B0','B1','B2']:
        p,z=nested_predictions(f,cols[label],a.target,classes,label);preds[label]=p;aud+=z
    pd.DataFrame(aud).to_json(out/'outer_fold_audit.json',orient='records',indent=2)
    # Prediction audit artifact.
    pr=f[['event_uid','research_trading_date','year','family_stack','poststrat_weight']].copy()
    if a.target=='reaction':
        pr['y']=y
        for k,p in preds.items():pr['p_'+k]=p
    else:
        pr['y']=y
        for k,p in preds.items():
            for j,c in enumerate(classes):pr[f'p_{k}_{c}']=p[:,j]
    pr.to_parquet(out/'crossfit_predictions.parquet',index=False,compression='zstd')
    weights={'family_balanced_event':family_balanced_weights(f),'population_event':population_weights(f),'session_balanced':session_weights(f)}
    metrics=[];losses={}
    for mode,w in weights.items():
        for label,p in preds.items():
            m,l=metric_bundle(f,y,p,a.target,classes,w);losses[(mode,label)]=l;metrics.append({'scope':'POOLED','weighting':mode,'model':label,'events':len(f),'sessions':f.research_trading_date.nunique(),**m})
    # Family-specific diagnostics from same pooled cross-fitted models.
    for fam,gidx in f.groupby('family_stack').groups.items():
        ii=np.array(list(gidx),int);sub=f.loc[ii];ys=y[ii];
        for mode in ['population_event','session_balanced']:
            w=population_weights(sub) if mode=='population_event' else session_weights(sub)
            for label,p in preds.items():
                pp=p[ii] if a.target=='reaction' else p[ii,:];m,_=metric_bundle(sub,ys,pp,a.target,classes,w);metrics.append({'scope':str(fam),'weighting':mode,'model':label,'events':len(sub),'sessions':sub.research_trading_date.nunique(),**m})
    pd.DataFrame(metrics).to_csv(out/'metrics.csv',index=False)
    annual=[]
    for yr in YEARS:
        ii=np.flatnonzero(f.year.to_numpy()==yr);sub=f.iloc[ii];w=family_balanced_weights(sub);ys=y[ii]
        for label,p in preds.items():
            pp=p[ii] if a.target=='reaction' else p[ii,:];m,_=metric_bundle(sub,ys,pp,a.target,classes,w);annual.append({'year':yr,'model':label,'events':len(ii),**m})
    adf=pd.DataFrame(annual);adf.to_csv(out/'annual_metrics.csv',index=False)
    comparisons=[]
    for old,new in [('B0','B1'),('B1','B2')]:
        rec={'comparison':f'{new}_vs_{old}'}
        for mode in weights:
            om=next(x for x in metrics if x['scope']=='POOLED' and x['weighting']==mode and x['model']==old);nm=next(x for x in metrics if x['scope']=='POOLED' and x['weighting']==mode and x['model']==new);rec[f'{mode}_logloss_improvement']=float(om['log_loss']-nm['log_loss'])
        yd=[]
        for yr in YEARS:
            om=adf[(adf.year==yr)&(adf.model==old)].iloc[0];nm=adf[(adf.year==yr)&(adf.model==new)].iloc[0];yd.append({'year':yr,'logloss_improvement':float(om.log_loss-nm.log_loss)})
        rec['year_deltas']=yd;rec['positive_years']=int(sum(z['logloss_improvement']>0 for z in yd));w=weights['family_balanced_event'];rec['cluster_bootstrap_95']=bootstrap_delta(f,losses[('family_balanced_event',old)],losses[('family_balanced_event',new)],w,2000);rec['directional_gate']=bool(rec['family_balanced_event_logloss_improvement']>0 and rec['session_balanced_logloss_improvement']>0 and rec['positive_years']>=5);comparisons.append(rec)
    family_deltas=[]
    mdf=pd.DataFrame(metrics)
    for fam in sorted(f.family_stack.astype(str).unique()):
        for old,new in [('B0','B1'),('B1','B2')]:
            for mode in ['population_event','session_balanced']:
                o=mdf[(mdf.scope==fam)&(mdf.weighting==mode)&(mdf.model==old)].iloc[0];n=mdf[(mdf.scope==fam)&(mdf.weighting==mode)&(mdf.model==new)].iloc[0];family_deltas.append({'family':fam,'comparison':f'{new}_vs_{old}','weighting':mode,'events':int(o.events),'sessions':int(o.sessions),'logloss_improvement':float(o.log_loss-n.log_loss)})
    pd.DataFrame(family_deltas).to_csv(out/'family_deltas.csv',index=False)
    result={'version':'COMEX_DEV_RANK1_PRIMARY_MODEL_RESULT_V1','target':a.target,'dataset':'B2 causally available events only','events':len(f),'sessions':int(f.research_trading_date.nunique()),'years':YEARS,'C_grid':C_GRID,'nested_validation':'outer LOYO; C chosen by inner LOYO on remaining years','training_weights':'poststratified and equal total influence per broad family','feature_counts':{'B0':len(cols['B0']),'B1_increment':len(b1),'B2_increment':len(b2)},'primary_exclusions':{'B1':sorted(B1_EXCLUDE),'B2':sorted(B2_EXCLUDE),'B2_secondary_N':'excluded from first primary fit'},'comparisons':comparisons,'interpretation':'DEV_RANK1 controlled discovery only; not independent final validation and not a trading strategy promotion.'}
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
