#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,time
from pathlib import Path
import pandas as pd
import databento as db

DATASET='GLBX.MDP3'; SYMBOL='GC.v.0'; STYPE='continuous'; PILOT_SPEND=4.01; CREDIT=125.0
M1_RANGES={
 'DEV':('2010-06-06','2019-01-01'),
 'CONFIRM':('2019-01-01','2023-01-01'),
 'LOCKED_TEST':('2023-01-01','2026-01-01'),
 'FORWARD_2026':('2026-01-01','2026-08-17'),
}

def sha(path):
    h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()

def split(y):
    if y<=2018:return 'RETRO_DEV'
    if y<=2022:return 'RETRO_CONFIRM'
    return 'LOCKED_COMEX_TEST'

def stage(row):
    if row['qa_only']: return 'QA_ONLY_ALREADY_PAID'
    y=int(row['year']); r=int(row['panel_rank_v4'])
    if y<=2018:return f'DEV_RANK{r}'
    if y<=2022:return 'CONFIRM'
    return 'LOCKED_TEST'

def mcost(c,schema,start,end):
    err=None
    for k in range(7):
        try:return float(c.metadata.get_cost(dataset=DATASET,symbols=SYMBOL,stype_in=STYPE,schema=schema,start=start,end=end))
        except Exception as e:err=e; time.sleep(min(20,2**k))
    raise RuntimeError(err)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--candidates',required=True); ap.add_argument('--panel',required=True); ap.add_argument('--costs',required=True); ap.add_argument('--pilot',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    cand=pd.read_csv(a.candidates); panel=pd.read_csv(a.panel); costs=pd.read_csv(a.costs); pilot=pd.read_csv(a.pilot); pdates=set(pilot.research_trading_date.astype(str))
    for c in ['year','quarter','vol_band']: cand[c]=pd.to_numeric(cand[c],errors='raise').astype(int)
    cand['date_ts']=pd.to_datetime(cand.research_trading_date); valid=cand[cand.date_ts.dt.weekday<5].copy()
    avail=valid.groupby(['year','quarter','vol_band']).size().rename('population_sessions').reset_index()
    panel['research_trading_date']=panel.research_trading_date.astype(str); panel['qa_only']=panel.research_trading_date.isin(pdates); panel['temporal_role']=panel.year.map(split); panel['acquisition_stage']=panel.apply(stage,axis=1)
    sel=panel.groupby(['year','quarter','vol_band']).agg(selected_sessions=('research_trading_date','size'),model_sessions=('qa_only',lambda x:int((~x).sum()))).reset_index()
    strata=avail.merge(sel,on=['year','quarter','vol_band'],how='left').fillna({'selected_sessions':0,'model_sessions':0}); strata['selected_sessions']=strata.selected_sessions.astype(int); strata['model_sessions']=strata.model_sessions.astype(int); strata['panel_inclusion_probability']=strata.selected_sessions/strata.population_sessions; strata['panel_weight']=strata.population_sessions/strata.selected_sessions.replace(0,pd.NA); strata['model_poststrat_weight']=strata.population_sessions/strata.model_sessions.replace(0,pd.NA)
    strata.to_csv(out/'stage1_strata_weights.csv',index=False)
    panel=panel.merge(strata[['year','quarter','vol_band','population_sessions','selected_sessions','model_sessions','panel_inclusion_probability','panel_weight','model_poststrat_weight']],on=['year','quarter','vol_band'],how='left')
    panel.to_csv(out/'stage1_sessions.csv',index=False)
    tc=costs[costs.schema.eq('trades')].copy(); tc['research_trading_date']=tc.research_trading_date.astype(str); panel=panel.merge(tc[['research_trading_date','cost_usd']],on='research_trading_date',how='left'); panel.loc[panel.qa_only,'cost_usd']=0.0
    if panel.loc[~panel.qa_only,'cost_usd'].isna().any(): raise SystemExit('missing trades cost for non-pilot session')
    stage_rows=[]
    for st,g in panel.groupby('acquisition_stage',sort=False): stage_rows.append({'stage':st,'sessions':int(len(g)),'qa_only_sessions':int(g.qa_only.sum()),'new_trades_cost_usd':float(g.cost_usd.fillna(0).sum())})
    key=os.environ.get('DATABENTO_API_KEY');
    if not key: raise SystemExit('DATABENTO_API_KEY missing')
    client=db.Historical(key); m1=[]
    for name,(start,end) in M1_RANGES.items():
        for schema in ['ohlcv-1m','bbo-1m']: m1.append({'stage_context':name,'schema':schema,'start':start,'end':end,'cost_usd':mcost(client,schema,start,end)})
    m1df=pd.DataFrame(m1); m1df.to_csv(out/'stage1_m1_costs.csv',index=False)
    sm={r['stage']:r for r in stage_rows}
    def m1sum(name): return float(m1df.loc[m1df.stage_context.eq(name),'cost_usd'].sum())
    sequence=[]; cum=PILOT_SPEND
    for st,ctx in [('DEV_RANK1','DEV'),('DEV_RANK2',None),('CONFIRM','CONFIRM'),('LOCKED_TEST','LOCKED_TEST')]:
        tr=float(sm.get(st,{}).get('new_trades_cost_usd',0)); context=m1sum(ctx) if ctx else 0.0; inc=tr+context; cum+=inc; sequence.append({'stage':st,'new_session_trades_usd':tr,'new_m1_context_usd':context,'incremental_cost_usd':inc,'cumulative_project_spend_usd':cum,'credit_remaining_from_125_usd':CREDIT-cum})
    forward=m1sum('FORWARD_2026')
    result={'version':'COMEX_V4_STAGE1_STAGED_PLAN_V1','metadata_only':True,'download_performed':False,'architecture':'TRADES primary; native A/B only; N retained explicitly with delta/CVD uncertainty bounds; TBBO deferred after QA pilot','corrected_panel_sessions':int(len(panel)),'qa_only_already_paid_sessions':int(panel.qa_only.sum()),'primary_model_sessions':int((~panel.qa_only).sum()),'stage_counts':stage_rows,'stage_sequence':sequence,'optional_forward_2026_m1_cost_usd':forward,'pilot_actual_spend_usd':PILOT_SPEND,'session_list_sha256':sha(out/'stage1_sessions.csv'),'strata_weights_sha256':sha(out/'stage1_strata_weights.csv'),'side_policy':{'native_A_B':'use as disseminated','native_N':'never silently impute in primary analysis','n_features':['N_volume_share','delta_lower_bound','delta_upper_bound','delta_sign_robust'],'tbbo_touch_rule':'pilot QA only / optional secondary sensitivity','reason':'Databento N may be structurally non-random; early-period BBO recovery precision was insufficient for primary imputation'},'temporal_policy':{'RETRO_DEV':'2011-2018; rank1 then rank2','RETRO_CONFIRM':'2019-2022; unopened until DEV transformations frozen','LOCKED_COMEX_TEST':'2023-2025; 3 QA pilot sessions excluded; remaining sessions unopened until complete model freeze','TRUE_FORWARD':'2026+ after final freeze'},'note':'All cost calculations are metadata-only. Stage purchases must be separately authorized. Twelve already-paid pilot dates are QA_ONLY and excluded from primary fitting/evaluation.'}
    (out/'stage1_staged_plan.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
