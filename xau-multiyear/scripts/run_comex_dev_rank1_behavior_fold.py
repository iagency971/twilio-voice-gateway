#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import run_comex_dev_rank1_primary_models as prim

CLASSES=['CLEAN_REJECTION','FAILED_AUCTION','ACCEPTED_BREAK','UNRESOLVED']
YEARS=list(range(2011,2019))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--outer-year',required=True,type=int);ap.add_argument('--model',choices=['B0','B1','B2'],required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    if a.outer_year not in YEARS:raise SystemExit('outer year must be 2011..2018')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    f=pd.read_parquet(a.features).copy();f=f[prim.asbool(f.b2_available)].copy().reset_index(drop=True);assert len(f)==30525 and sorted(f.year.unique().tolist())==YEARS
    cols,_,_=prim.primary_columns(f);fs=cols[a.model]
    train=f[f.year!=a.outer_year];test=f[f.year==a.outer_year]
    C,inner=prim.choose_c(train,fs,'behavior',CLASSES)
    prep,_,_=prim.make_preprocessor(train,fs);xt=prep.fit_transform(prim.clean_X(train,fs));xv=prep.transform(prim.clean_X(test,fs));yt=prim.target_array(train,'behavior');wt=prim.family_balanced_weights(train);m=prim.model_for('behavior',C);m.fit(xt,yt,sample_weight=wt);raw=m.predict_proba(xv);p=prim.align_proba(m,raw,CLASSES)
    pr=test[['event_uid','research_trading_date','year','family_stack','poststrat_weight']].copy();pr['y']=test.behavior_v2.astype(str).to_numpy()
    for j,c in enumerate(CLASSES):pr[f'p_{a.model}_{c}']=p[:,j]
    pr.to_parquet(out/f'pred_{a.model}_{a.outer_year}.parquet',index=False,compression='zstd')
    audit={'target':'behavior','model':a.model,'outer_year':a.outer_year,'selected_C':C,'inner_logloss_by_C':{str(k):v for k,v in inner.items()},'train_events':len(train),'test_events':len(test),'solver':'lbfgs','max_iter':500,'scientific_equivalence':'exact functions imported from run_comex_dev_rank1_primary_models.py'}
    (out/f'audit_{a.model}_{a.outer_year}.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
