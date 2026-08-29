#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,sys,tempfile
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('me',HERE/'xau_e_display_episode_model_eval_v1.py')
me=importlib.util.module_from_spec(spec);sys.modules[spec.name]=me;spec.loader.exec_module(me)


def data(n=400):
    rows=[];fams=['EPM_M1_R2_A8H','ESM_BOTH_G120M','EWM_G60M','ES_M1_8H_R2_T0.50']
    for i in range(n):
        w=.2+(i%40)/20.;p=1+(i%12);f=fams[i%4];latent=1.2*w+.12*np.log1p(p)+(i%4)*.08;y=int((latent+(i%7)*.08)>1.55)
        rows.append({'zone_width_v':w,'display_persistence_c5':p,'current_family':f,'primary_binary_label':y,'session_date_ny':f'2026-01-{1+(i//8)%28:02d}'})
    return pd.DataFrame(rows)


def run():
    d=data();m,fit,qa=me.fit_dev(d);sc,sqa=me.transform_score(fit,m);checks={}
    checks['three_source_features_only']=me.FEATURES==['zone_width_v','display_persistence_c5','current_family']
    checks['population_sd_positive']=m.width_sd>0 and m.logpers_sd>0
    checks['lexicographic_reference']=m.reference_category==sorted(m.categories)[0]
    checks['quartiles_strict']=m.quartiles[0]<m.quartiles[1]<m.quartiles[2]
    checks['rank_bounds']=bool(((sc['E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1']>=0)&(sc['E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1']<=1)).all())
    checks['association_definition']=abs(me.auc_assoc(sc)-(me.roc_auc_score(sc.primary_binary_label,sc.continuous_logit)-.5))<1e-15
    b=me.bootstrap(sc,me.auc_assoc,n=100,seed=me.SEED);checks['cluster_bootstrap_requested_exact']=b['requested']==100 and b['valid']+b['invalid']==100
    q=me.quartile_rates(sc);checks['fixed_quartile_labels']=set(q)=={'Q1','Q2','Q3','Q4'} and all(q[x]['n']>0 for x in q)
    later=d.iloc[:20].copy();later['current_family']='UNSEEN_FAMILY';later_sc,lqa=me.transform_score(later,m);checks['unseen_family_counted']=lqa['unseen_family_rate']==1.0 and len(later_sc)==20
    miss=d.iloc[:10].copy();miss.loc[0,'zone_width_v']=np.nan;_,mqa=me.transform_score(miss,m);checks['missing_feature_excluded']=mqa['feature_excluded_rows']==1 and abs(mqa['feature_exclusion_rate']-.1)<1e-12
    blocks=me.prospective_blocks(sc);sizes=[b['session_n'] for b in blocks];flat=[s for b in blocks for s in b['sessions']];checks['prospective_blocks_complete_sessions']=len(flat)==len(set(flat))==sc.session_date_ny.nunique() and max(sizes)-min(sizes)<=1
    checks['separate_dev_replication_tokens']=me.GO_DEV_TOKEN!=me.GO_REPLICATION_TOKEN
    # Frozen model round-trip must be exact enough to reproduce logits/ranks without refit.
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'m.json';p.write_text(json.dumps(me.model_json(m),sort_keys=True));m2=me.load_model(str(p));sc2,_=me.transform_score(fit,m2)
        checks['frozen_model_roundtrip_scores']=bool(np.array_equal(sc.continuous_logit.to_numpy(),sc2.continuous_logit.to_numpy())) and bool(np.array_equal(sc['E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1'].to_numpy(),sc2['E_DISPLAY_EPISODE_REACTION_RANK_US_BUY_V1'].to_numpy()))
    # Contact-time window authority is explicit.
    x=pd.DataFrame({'contact_bar_open_time_utc':['2024-08-02T13:00:00Z']});ok=True
    try:me.assert_contact_window(x,me.DEV_START,me.DEV_END,'DEV')
    except RuntimeError:ok=False
    checks['dev_contact_window_accepts_inside']=ok
    failed=False
    try:me.assert_contact_window(x,me.REP_START,me.REP_END,'REP')
    except RuntimeError:failed=True
    checks['wrong_contact_window_fails_closed']=failed
    passed=all(checks.values());out={'status':'SYNTHETIC_MODEL_EVAL_V1_PASS' if passed else 'SYNTHETIC_MODEL_EVAL_V1_FAIL','checks':checks,'real_outcomes_used':False}
    print(json.dumps(out,indent=2,sort_keys=True))
    if not passed:raise SystemExit(2)

if __name__=='__main__':run()
