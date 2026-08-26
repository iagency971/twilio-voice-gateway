#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, hashlib
from pathlib import Path
import joblib
import numpy as np


def args():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--output',required=True);return p.parse_args()

def main():
    a=args();p=Path(a.model);art=joblib.load(p)
    pipe=art['pipeline'];pre=pipe.named_steps['pre'];clf=pipe.named_steps['clf']
    num=pre.named_transformers_['num'];cat=pre.named_transformers_['cat']
    impute=num.named_steps['impute'];scale=num.named_steps['scale'];ohe=cat.named_steps['ohe'];cat_imp=cat.named_steps['impute']
    numeric=list(art['numeric_features']);categorical=list(art['categorical_features'])
    names=[str(x) for x in pre.get_feature_names_out()]
    coef=np.asarray(clf.coef_[0],float);inter=float(clf.intercept_[0])
    if len(names)!=len(coef):raise RuntimeError((len(names),len(coef)))
    cdf=np.asarray(art['train_score_cdf_sorted'],float);n=len(cdf)
    eth=[]
    for k in range(1,101):
        idx=max(0,min(n-1,int(math.ceil(k*n/100.0))-1));eth.append(float(cdf[idx]))
    # Manual parity at the deterministic imputer/first-category point.
    xnum=np.asarray(impute.statistics_,float)
    z=(xnum-np.asarray(scale.mean_,float))/np.asarray(scale.scale_,float)
    xcat=[]
    for cats in ohe.categories_:
        q=np.zeros(len(cats),float);q[0]=1.0;xcat.extend(q.tolist())
    transformed=np.r_[z,np.asarray(xcat,float)]
    logit=inter+float(np.dot(coef,transformed));manual=1.0/(1.0+math.exp(-logit))
    row={numeric[i]:float(xnum[i]) for i in range(len(numeric))}
    for i,c in enumerate(categorical):row[c]=str(ohe.categories_[i][0])
    import pandas as pd
    predicted=float(pipe.predict_proba(pd.DataFrame([row])[numeric+categorical])[:,1][0])
    if abs(manual-predicted)>1e-12:raise RuntimeError((manual,predicted))
    out={
      'status':'E_BUY_US_PINE_MODEL_EXPORT_PASS','source_model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
      'model_id':art['model_id'],'numeric_features':numeric,'categorical_features':categorical,
      'numeric_imputer_median':[float(x) for x in impute.statistics_],
      'numeric_scaler_mean':[float(x) for x in scale.mean_],
      'numeric_scaler_scale':[float(x) for x in scale.scale_],
      'categorical_imputer_statistics':[str(x) for x in cat_imp.statistics_],
      'categorical_categories':{categorical[i]:[str(x) for x in cats] for i,cats in enumerate(ohe.categories_)},
      'transformed_feature_names':names,'logistic_intercept':inter,'logistic_coef':[float(x) for x in coef],
      'training_score_count':n,'e_integer_ge_threshold_probability':eth,
      'e80_probability_threshold':eth[79],'e90_probability_threshold':eth[89],
      'manual_pipeline_parity_abs_error':abs(manual-predicted),
      'mapping_note':'E floor integer = highest k in 1..100 with probability >= threshold[k-1]; E>=80/E>=90 are exact empirical-CDF cut classifications subject only to float precision.'
    }
    Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps({'status':out['status'],'features':len(names),'cdf_n':n,'e80':out['e80_probability_threshold'],'e90':out['e90_probability_threshold'],'manual_error':out['manual_pipeline_parity_abs_error']},indent=2))
if __name__=='__main__':main()
