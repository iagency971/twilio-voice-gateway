#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,warnings
from pathlib import Path
import numpy as np,pandas as pd,scipy,sklearn
from scipy.stats import spearmanr
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import xau_e_zone_v2_stats as st

TOKEN='GO_E_ZONE_SCORE_BUY_US_V2_SEQUENTIAL_HISTORICAL_EXECUTION'
NUM_NUIS=['log1p_zone_width_v','log1p_zone_width_v_squared','distance_v','distance_v_squared','log_v_snapshot','nearest_upper_z4_dist_v','trend15_v','trend60_v','trend240_v']
CAT_NUIS=['display_slot_rank','minute_bin_30m','upper_z4_count_bucket','weekday_ny']
NUM_STR=['native_evidence_family_percentile','log1p_display_persistence_c5','confluence_count_e_families','center_stability_3_c5']
CAT_STR=['current_family']
REQ_RAW=['zone_width_v','display_persistence_c5','native_evidence_raw','confluence_count_e_families','center_stability_3_c5','current_family']+NUM_NUIS+CAT_NUIS

def args():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['DEV_FIT','EVALUATE'],required=True);p.add_argument('--labels',required=True);p.add_argument('--model-json',required=True);p.add_argument('--report-json',required=True);p.add_argument('--scored-output',required=True);p.add_argument('--authorization-token',default='');return p.parse_args()

def env():return {'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'scikit_learn':sklearn.__version__}
def primary(path):
 d=pd.read_csv(path,compression='infer',float_precision='round_trip');d=d[d.selection_status=='PRIMARY_CONTACT'].copy();return d

def midrank_against(ref,x):
 r=np.sort(np.asarray(ref,float));x=np.asarray(x,float);l=np.searchsorted(r,x,'left');u=np.searchsorted(r,x,'right');return (l+.5*(u-l))/len(r)

def prep_base(d, native_refs=None, fit=False):
 x=d.copy();before=len(x);miss=x[[c for c in REQ_RAW if c in x.columns]].isna().any(axis=1)
 x=x.loc[~miss].copy();qa={'input_rows':int(before),'feature_excluded_rows':int(miss.sum()),'feature_exclusion_rate':float(miss.mean()) if before else None}
 x['log1p_display_persistence_c5']=np.log1p(x.display_persistence_c5.astype(float))
 if fit:
  refs={}
  vals=np.zeros(len(x),float)
  for fam,g in x.groupby('current_family',sort=True):
   idx=g.index;raw=g.native_evidence_raw.astype(float).to_numpy()
   if str(fam)=='ESM_BOTH_G120M':refs[str(fam)]=[1.0];vals[x.index.get_indexer(idx)]=.5
   else:refs[str(fam)]=sorted(raw.tolist());vals[x.index.get_indexer(idx)]=midrank_against(refs[str(fam)],raw)
  x['native_evidence_family_percentile']=vals;native_refs=refs
 else:
  vals=[];unseen=0
  for _,r in x.iterrows():
   fam=str(r.current_family)
   if fam not in native_refs:vals.append(.5);unseen+=1
   elif fam=='ESM_BOTH_G120M':vals.append(.5)
   else:vals.append(float(midrank_against(native_refs[fam],[float(r.native_evidence_raw)])[0]))
  x['native_evidence_family_percentile']=vals;qa['unseen_family_rows']=unseen;qa['unseen_family_rate']=float(unseen/len(x)) if len(x) else None
 return x,qa,native_refs

def fit_encoder(x,num,cat):
 spec={'num':{},'cat':{}};cols=[];names=[]
 for c in num:
  v=x[c].astype(float).to_numpy();mu=float(v.mean());sd=float(v.std(ddof=0));sd=sd if np.isfinite(sd) and sd>0 else 1.0;spec['num'][c]=[mu,sd];cols.append((v-mu)/sd);names.append(c+'__z')
 for c in cat:
  vals=x[c].astype(str);cats=sorted(vals.unique().tolist());spec['cat'][c]=cats
  for k in cats[1:]:cols.append((vals.to_numpy()==k).astype(float));names.append(f'{c}__{k}')
 return np.column_stack(cols) if cols else np.zeros((len(x),0)),spec,names

def transform_encoder(x,spec,num,cat):
 cols=[];names=[];unseen={}
 for c in num:
  mu,sd=spec['num'][c];cols.append((x[c].astype(float).to_numpy()-mu)/sd);names.append(c+'__z')
 for c in cat:
  cats=spec['cat'][c];v=x[c].astype(str).to_numpy();unseen[c]=int((~np.isin(v,np.array(cats,dtype=object))).sum())
  for k in cats[1:]:cols.append((v==k).astype(float));names.append(f'{c}__{k}')
 return (np.column_stack(cols) if cols else np.zeros((len(x),0))),names,unseen

def fit_logit(X,y):
 m=LogisticRegression(penalty='l2',C=1.0,solver='lbfgs',max_iter=5000,class_weight=None,fit_intercept=True)
 with warnings.catch_warnings(record=True) as w:warnings.simplefilter('always');m.fit(X,y)
 conv=[str(z.message) for z in w if issubclass(z.category,ConvergenceWarning)]
 if conv or int(np.max(m.n_iter_))>=5000:raise RuntimeError(f'convergence fail {conv}')
 return m

def quartile(d):
 out={}
 for q in ['Q1','Q2','Q3','Q4']:
  g=d[d.fixed_quartile==q];out[q]={'n':int(len(g)),'rate':float(g.primary_binary_label.mean()) if len(g) else None}
 return out

def metric_delta(d):
 if not len(d) or d.primary_binary_label.nunique()!=2:return None
 y=d.primary_binary_label.astype(int);return float(roc_auc_score(y,d.full_logit)-roc_auc_score(y,d.nuisance_logit))
def metric_auc(d):return st.auc(d,'displayed_raw_score')
def metric_q(d):return st.q4q1(d)
def width_quintiles(d,bounds):
 bins=[-np.inf]+list(bounds)+[np.inf];z=d.copy();z['width_quintile']=pd.cut(z.zone_width_v.astype(float),bins=bins,labels=['W1','W2','W3','W4','W5'],include_lowest=True)
 return {w:metric_q(z[z.width_quintile==w]) for w in ['W1','W2','W3','W4','W5']}
def eval_report(d,qa,width_bounds):
 ev={'n':int(len(d)),'sessions':int(d.session_date_ny.nunique()),'displayed_auc':metric_auc(d),'displayed_auc_bootstrap':st.session_bootstrap(d,metric_auc),
     'quartiles':quartile(d),'q4_minus_q1':metric_q(d),'q4_minus_q1_bootstrap':st.session_bootstrap(d,metric_q,seed=st.SEED+11),
     'full_auc':float(roc_auc_score(d.primary_binary_label,d.full_logit)),'nuisance_auc':float(roc_auc_score(d.primary_binary_label,d.nuisance_logit)),'full_minus_nuisance_auc':metric_delta(d),'delta_bootstrap':st.session_bootstrap(d,metric_delta,seed=st.SEED+23)}
 ev['score_width_spearman']=float(spearmanr(d.displayed_raw_score,d.zone_width_v).statistic);within={}
 for fam,g in d.groupby('current_family'):
  if len(g)>=200:within[str(fam)]={'n':int(len(g)),'rho':float(spearmanr(g.displayed_raw_score,g.zone_width_v).statistic)}
 ev['within_family_score_width_spearman']=within;ev['width_quintile_q4_minus_q1']=width_quintiles(d,width_bounds)
 rates=[ev['quartiles'][q]['rate'] for q in ['Q1','Q2','Q3','Q4']];w=list(ev['width_quintile_q4_minus_q1'].values())
 checks={'n_ge_1000':len(d)>=1000,'sessions_ge_90':d.session_date_ny.nunique()>=90,'displayed_auc_gt_05':ev['displayed_auc']>.5,'displayed_auc_ci_lower_gt_05':ev['displayed_auc_bootstrap']['ci95'][0] is not None and ev['displayed_auc_bootstrap']['ci95'][0]>.5,
 'quartiles_monotone':all(v is not None for v in rates) and rates[0]<=rates[1]<=rates[2]<=rates[3],'q4_q1_gt_0':ev['q4_minus_q1'] is not None and ev['q4_minus_q1']>0,'q4_q1_ci_lower_gt_0':ev['q4_minus_q1_bootstrap']['ci95'][0] is not None and ev['q4_minus_q1_bootstrap']['ci95'][0]>0,
 'full_minus_nuisance_gt_0':ev['full_minus_nuisance_auc']>0,'full_minus_nuisance_ci_lower_gt_0':ev['delta_bootstrap']['ci95'][0] is not None and ev['delta_bootstrap']['ci95'][0]>0,
 'feature_exclusion_le_02':qa['feature_exclusion_rate'] is not None and qa['feature_exclusion_rate']<=.02,'unseen_family_le_05':qa.get('unseen_family_rate',0)<=.05,
 'abs_score_width_rho_le_020':abs(ev['score_width_spearman'])<=.20,'within_family_abs_rho_le_030':all(abs(z['rho'])<=.30 for z in within.values()),
 'width_quintiles_4_of_5_positive':sum(v is not None and v>0 for v in w)>=4,'no_width_quintile_below_minus_002':all(v is not None and v>=-.02 for v in w)}
 ev['checks']=checks;ev['score_pass']=all(checks.values())
 slots={}
 for s,g in d.groupby('display_slot_rank'):
  slots[str(int(s))]={'n':int(len(g)),'auc':metric_auc(g),'q4_minus_q1':metric_q(g),'quartiles':quartile(g)}
 ev['slot_diagnostics']=slots;return ev

def save_scored(d,path):
 Path(path).parent.mkdir(parents=True,exist_ok=True);d.to_csv(path,index=False,compression={'method':'gzip','mtime':0},float_format='%.17g')

def main():
 a=args()
 if a.authorization_token!=TOKEN:raise RuntimeError('V2_MODEL_EXECUTION_BLOCKED')
 d=primary(a.labels)
 if a.phase=='DEV_FIT':
  x,qa,refs=prep_base(d,fit=True);Xn,sn,nn=fit_encoder(x,NUM_NUIS,CAT_NUIS);Xs,ss,ns=fit_encoder(x,NUM_STR,CAT_STR);Xf=np.column_stack([Xn,Xs]);y=x.primary_binary_label.astype(int).to_numpy();mn=fit_logit(Xn,y);mf=fit_logit(Xf,y)
  x['nuisance_logit']=mn.decision_function(Xn);x['full_logit']=mf.decision_function(Xf);beta=mf.coef_[0];x['displayed_raw_score']=Xs.dot(beta[len(nn):]);raw=x.displayed_raw_score.to_numpy(float);qs=np.quantile(raw,[.25,.5,.75],method='linear').tolist();wq=np.quantile(x.zone_width_v.astype(float),[.2,.4,.6,.8],method='linear').tolist()
  x['strength_score_0_100']=100*midrank_against(raw,raw);q1,q2,q3=qs;x['fixed_quartile']=np.where(raw<=q1,'Q1',np.where(raw<=q2,'Q2',np.where(raw<=q3,'Q3','Q4')))
  model={'status':'E_ZONE_SCORE_BUY_US_V2_DEV_MODEL_FROZEN','native_evidence_refs':refs,'nuisance_encoder':sn,'strength_encoder':ss,'nuisance_feature_names':nn,'strength_feature_names':ns,'nuisance_coef':mn.coef_[0].tolist(),'nuisance_intercept':float(mn.intercept_[0]),'full_coef':mf.coef_[0].tolist(),'full_intercept':float(mf.intercept_[0]),'displayed_score_dev_distribution':raw.tolist(),'displayed_score_quartiles':qs,'width_quintile_cutpoints':wq,'nuisance_n_iter':int(mn.n_iter_[0]),'full_n_iter':int(mf.n_iter_[0]),'environment':env(),'replication_used_to_fit':False}
  qa['unseen_family_rate']=0.0;ev=eval_report(x,qa,wq);report={'status':'E_ZONE_SCORE_BUY_US_V2_DEV_FIT_COMPLETE','environment':env(),'qa':qa,'evaluation':ev,'model_frozen':True}
  Path(a.model_json).write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
 else:
  model=json.load(open(a.model_json));x,qa,_=prep_base(d,native_refs=model['native_evidence_refs'],fit=False);Xn,nn,un=transform_encoder(x,model['nuisance_encoder'],NUM_NUIS,CAT_NUIS);Xs,ns,un2=transform_encoder(x,model['strength_encoder'],NUM_STR,CAT_STR);qa['unseen_family_rows']=un2.get('current_family',0);qa['unseen_family_rate']=qa['unseen_family_rows']/len(x) if len(x) else None
  bn=np.asarray(model['nuisance_coef'],float);bf=np.asarray(model['full_coef'],float);x['nuisance_logit']=float(model['nuisance_intercept'])+Xn.dot(bn);x['full_logit']=float(model['full_intercept'])+np.column_stack([Xn,Xs]).dot(bf);x['displayed_raw_score']=Xs.dot(bf[len(nn):]);ref=np.asarray(model['displayed_score_dev_distribution'],float);x['strength_score_0_100']=100*midrank_against(ref,x.displayed_raw_score);q1,q2,q3=model['displayed_score_quartiles'];x['fixed_quartile']=np.where(x.displayed_raw_score<=q1,'Q1',np.where(x.displayed_raw_score<=q2,'Q2',np.where(x.displayed_raw_score<=q3,'Q3','Q4')));ev=eval_report(x,qa,model['width_quintile_cutpoints']);report={'status':'E_ZONE_SCORE_BUY_US_V2_FROZEN_MODEL_EVALUATION_COMPLETE','environment':env(),'qa':qa,'evaluation':ev,'model_loaded_no_refit':True}
 save_scored(x,a.scored_output);Path(a.report_json).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2,sort_keys=True))
if __name__=='__main__':main()
