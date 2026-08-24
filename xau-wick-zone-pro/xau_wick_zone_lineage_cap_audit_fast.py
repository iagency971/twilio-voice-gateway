import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr
CAPS=(96,128,160,192)

def parse():
 p=argparse.ArgumentParser();p.add_argument('--pkl',required=True);p.add_argument('--frozen-json',required=True);p.add_argument('--output',required=True);return p.parse_args()

def dec(D):
 D=D.copy();D['time']=pd.to_datetime(D.time,utc=True)
 for out,col in [('log_prom','prominence'),('log_bg','background'),('log_strength','strength_raw'),('log_mass','mass'),('log_peak','peak_height'),('log_mean_wick','mean_wick'),('log_mean_body','mean_body')]:D[out]=np.log1p(D[col])
 D['log_age_active']=np.log1p(D.age_active_min);D['log_age_civil']=np.log1p(D.age_civil_min);return D

def sig(x):
 x=np.asarray(x,float);o=np.empty_like(x);m=x>=0;o[m]=1/(1+np.exp(-x[m]));e=np.exp(x[~m]);o[~m]=e/(1+e);return o

def pred(D,p):
 X=D[p['features']].to_numpy(float);mu=np.array(p['scaler_mean']);sd=np.array(p['scaler_scale']);c=np.array(p['coef']);return sig(float(p['intercept'])+((X-mu)/sd)@c)

def qs(x,ps):return {str(v):float(np.quantile(x,v)) for v in ps}

def capped(D,cap):
 C=D.copy();n=len(C);aa=np.zeros(n);ac=np.zeros(n);pv=np.ones(n);rs=np.zeros(n,np.int64);al=np.ones(n,np.int64)
 for _,g in C.groupby('lineage_id',sort=False):
  idx=g.sort_values('landmark_i',kind='mergesort').index.to_numpy(np.int64);m=len(idx);j=np.arange(m);k=np.maximum(0,j-cap+1)
  lm=C.loc[idx,'landmark_i'].to_numpy(np.int64);tm=C.loc[idx,'time'].astype('int64').to_numpy(np.int64);pr=C.loc[idx,'prominence'].to_numpy(float);fs=C.loc[idx,'reinforce_streak'].to_numpy(np.int64)
  aa[idx]=(lm-lm[k]).astype(float);ac[idx]=(tm-tm[k])/60_000_000_000.0;al[idx]=j-k+1
  mx=pd.Series(pr).rolling(cap,min_periods=1).max().to_numpy();pv[idx]=pr/(mx+1e-9);rs[idx]=np.minimum(fs,j-k)
 C['age_active_min']=aa;C['age_civil_min']=ac;C['prom_vs_histmax']=pv;C['reinforce_streak']=rs;C['age_lm_cap']=al;C['log_age_active']=np.log1p(aa);C['log_age_civil']=np.log1p(ac);return C

def lmm(D,a,b):
 T=pd.DataFrame({'lm':D.landmark_i.to_numpy(),'a':a,'b':b},index=D.index);sp=[];t1=[];j3=[]
 for _,g in T.groupby('lm',sort=False):
  t1.append(g.a.idxmax()==g.b.idxmax())
  if len(g)>=3:
   s=spearmanr(g.a,g.b).statistic
   if np.isfinite(s):sp.append(s)
   A=set(g.nlargest(3,'a').index);B=set(g.nlargest(3,'b').index);j3.append(len(A&B)/len(A|B))
 return {'within_landmark_spearman_median':float(np.median(sp)),'within_landmark_spearman_mean':float(np.mean(sp)),'within_landmark_n':len(sp),'top1_agreement':float(np.mean(t1)),'top1_landmarks':len(t1),'top3_jaccard_mean':float(np.mean(j3)),'top3_jaccard_median':float(np.median(j3)),'top3_landmarks':len(j3)}

def main():
 a=parse();D=dec(pd.read_pickle(a.pkl).reset_index(drop=True));f=json.load(open(a.frozen_json));p=f['feeds']['BID']['M0GL'];full=pred(D,p);age=D.age_lm.to_numpy(np.int64)
 ar={'max':int(age.max()),'quantiles':qs(age,(.5,.75,.9,.95,.99,.995,.999)),'fractions_gt':{str(c):float(np.mean(age>c)) for c in CAPS},'rows':len(D),'lineages':int(D.lineage_id.nunique()),'landmarks':int(D.landmark_i.nunique())}
 outc={};sel=None
 for cap in CAPS:
  C=capped(D,cap);s=pred(C,p);e=np.abs(s-full);m={'cap':cap,'pearson':float(pearsonr(full,s).statistic),'spearman':float(spearmanr(full,s).statistic),'abs_error_quantiles':qs(e,(.5,.9,.95,.99)),'fraction_abs_error_gt_003':float(np.mean(e>.03)),'fraction_abs_error_gt_005':float(np.mean(e>.05)),'fraction_full_age_gt_cap':float(np.mean(age>cap)),**lmm(D,full,s)}
  ck={'spearman_ge_0995':m['spearman']>=.995,'pearson_ge_0995':m['pearson']>=.995,'median_abs_error_le_0005':m['abs_error_quantiles']['0.5']<=.005,'p95_abs_error_le_0030':m['abs_error_quantiles']['0.95']<=.03,'fraction_abs_error_gt_005_le_002':m['fraction_abs_error_gt_005']<=.02,'within_landmark_spearman_median_ge_0995':m['within_landmark_spearman_median']>=.995,'top1_agreement_ge_095':m['top1_agreement']>=.95,'top3_jaccard_mean_ge_095':m['top3_jaccard_mean']>=.95};m['checks']=ck;m['status']='PASS' if all(ck.values()) else 'FAIL';outc[str(cap)]=m
  if sel is None and m['status']=='PASS':sel=cap
 out={'status':'PASS' if sel is not None else 'FAIL','scope':'OUTCOME_BLIND_PINE_LINEAGE_BOOTSTRAP_CAP_DEV_BID_JAN_JUL_2024','future_outcomes_used':False,'candidate_caps':list(CAPS),'selection_rule':'smallest cap passing every preregistered engineering criterion','selected_cap':sel,'full_lineage_age':ar,'caps':outc,'implementation':'vectorized equivalent of preregistered cold-start state definition'}
 Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
