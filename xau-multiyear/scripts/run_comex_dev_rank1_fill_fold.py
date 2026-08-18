#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
import run_comex_dev_rank1_primary_models as prim
import run_comex_dev_rank1_fill_model as fill

YEARS=list(range(2011,2019))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--features',required=True);ap.add_argument('--outer-year',required=True,type=int);ap.add_argument('--model',choices=['B0','B1','B2'],required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    if a.outer_year not in YEARS:raise SystemExit('outer year must be 2011..2018')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);f=pd.read_parquet(a.features).copy();models=f.entry_model.astype(str).unique().tolist();assert len(models)==1,models;entry_model=models[0];f['b2_available_bool']=prim.asbool(f.b2_available);f=f[f.b2_available_bool].copy().reset_index(drop=True);assert sorted(f.year.unique().tolist())==YEARS
    feas=fill.feasibility(f);assert feas.get('identifiable',False),f'{entry_model} frozen nested fill target non-identifiable'
    cols,_,_=prim.primary_columns(f);fs=cols[a.model];train=f[f.year!=a.outer_year];test=f[f.year==a.outer_year];C,inner=fill.choose_c(train,fs);prep,_,_=prim.make_preprocessor(train,fs);xt=prep.fit_transform(prim.clean_X(train,fs));xv=prep.transform(prim.clean_X(test,fs));m=prim.model_for('reaction',C);m.fit(xt,fill.yarr(train),sample_weight=prim.family_balanced_weights(train));raw=m.predict_proba(xv);j=list(m.classes_).index(1);p=raw[:,j]
    pr=test[['event_uid','research_trading_date','year','family_stack','poststrat_weight']].copy();pr['y']=fill.yarr(test);pr[f'p_{a.model}']=p;pr.to_parquet(out/f'pred_{a.model}_{a.outer_year}.parquet',index=False,compression='zstd')
    audit={'target':'fill_or_entry','entry_model':entry_model,'model':a.model,'outer_year':a.outer_year,'selected_C':C,'inner_logloss_by_C':{str(k):v for k,v in inner.items()},'train_events':len(train),'test_events':len(test),'train_fill':int(fill.yarr(train).sum()),'test_fill':int(fill.yarr(test).sum()),'scientific_equivalence':'exact functions imported from frozen fill runner'};(out/f'audit_{a.model}_{a.outer_year}.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
