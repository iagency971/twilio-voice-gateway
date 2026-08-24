import argparse,glob,json,math
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr

STEP=.01; LOOKBACK=1440;HORIZON=240;REACT_MAX=60;EPS=1e-9

def parse():
 p=argparse.ArgumentParser();p.add_argument('--pkl',required=True);p.add_argument('--files',nargs='+',required=True);p.add_argument('--frozen-json',required=True);p.add_argument('--output',required=True);return p.parse_args()

def dec(D):
 D=D.copy();D['time']=pd.to_datetime(D.time,utc=True)
 for out,col in [('log_prom','prominence'),('log_bg','background'),('log_strength','strength_raw'),('log_mass','mass'),('log_peak','peak_height'),('log_mean_wick','mean_wick'),('log_mean_body','mean_body')]:D[out]=np.log1p(D[col])
 D['log_age_active']=np.log1p(D.age_active_min);D['log_age_civil']=np.log1p(D.age_civil_min);return D

def sig(x):
 x=np.asarray(x,float);o=np.empty_like(x);m=x>=0;o[m]=1/(1+np.exp(-x[m]));e=np.exp(x[~m]);o[~m]=e/(1+e);return o

def pred(D,p):
 X=D[p['features']].to_numpy(float);mu=np.array(p['scaler_mean']);sd=np.array(p['scaler_scale']);c=np.array(p['coef']);return sig(float(p['intercept'])+((X-mu)/sd)@c)

def eligible_from_files(pats):
 fs=[]
 for pat in pats:
  for f in sorted(glob.glob(pat)):
   d=pd.read_csv(f);d['time']=pd.to_datetime(d.timestamp,unit='ms',utc=True);fs.append(d[['time','open','high','low','close']])
 d=pd.concat(fs,ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True);a=d[d.high>d.low].reset_index(drop=True);T=a.time
 ok=[];N=len(a)
 for i in range(LOOKBACK-1,N-HORIZON-REACT_MAX):
  t=T.iloc[i]
  if t.minute%15==0 and t.second==0:ok.append(i)
 return ok

def greedy_states(Z,eligible):
 n=len(Z);lin=np.zeros(n,np.int64);age=np.ones(n,np.int64);aa=np.zeros(n);ac=np.zeros(n);cs=np.zeros(n);wc=np.zeros(n);pc=np.zeros(n);mc=np.zeros(n);sc=np.zeros(n);rein=np.zeros(n,np.int64);sd4=np.zeros(n);cv4=np.zeros(n);pvm=np.ones(n);plink=np.full(n,-1,np.int64)
 center=Z.center.to_numpy(float);lo=Z.zlo.to_numpy(float);hi=Z.zhi.to_numpy(float);vs=Z.vseg.to_numpy(float);prom=Z.prominence.to_numpy(float);mass=Z.mass.to_numpy(float);strength=Z.strength_raw.to_numpy(float);times=Z.time.to_numpy()
 by={int(k):g.index.to_numpy(np.int64) for k,g in Z.groupby('landmark_i',sort=True)};groups=[by.get(int(lm),np.array([],dtype=np.int64)) for lm in eligible]
 nextid=1;prev=np.array([],dtype=np.int64);states={}
 for lm,cur in zip(eligible,groups):
  lm=int(lm)
  if len(cur)==0:
   prev=np.array([],dtype=np.int64);continue
  assign={}
  pairs=[]
  for pi in prev:
   pw=max(hi[pi]-lo[pi],STEP)
   for ci in cur:
    cw=max(hi[ci]-lo[ci],STEP);cd=abs(center[pi]-center[ci]);v=max(vs[pi],vs[ci],STEP);inter=max(0.,min(hi[pi],hi[ci])-max(lo[pi],lo[ci]));union=max(hi[pi],hi[ci])-min(lo[pi],lo[ci]);iou=inter/union if union>0 else 0.
    if cd<=v or iou>0:
     cost=cd/v+.5*(1-iou)+.1*abs(math.log(cw/pw));pairs.append((cost,int(pi),int(ci)))
  pairs.sort(key=lambda x:(x[0],x[1],x[2]));usedp=set();usedc=set()
  for _,pi,ci in pairs:
   if pi not in usedp and ci not in usedc:assign[ci]=pi;usedp.add(pi);usedc.add(ci)
  for ci0 in cur:
   ci=int(ci0)
   if ci in assign:
    pi=assign[ci];plink[ci]=pi;lid=int(lin[pi]);st=states[lid];ag=st['age']+1;streak=st['streak']+1 if prom[ci]>prom[pi] else 0;centers=(st['centers']+[center[ci]])[-4:];widths=(st['widths']+[hi[ci]-lo[ci]])[-4:];histmax=max(st['prommax'],prom[ci])
    lin[ci]=lid;age[ci]=ag;aa[ci]=float(lm-st['first_lm']);ac[ci]=(pd.Timestamp(times[ci])-pd.Timestamp(st['first'])).total_seconds()/60;cs[ci]=abs(center[ci]-center[pi])/max(vs[ci],STEP);wc[ci]=math.log(max(hi[ci]-lo[ci],STEP)/max(hi[pi]-lo[pi],STEP));pc[ci]=math.log1p(prom[ci])-math.log1p(prom[pi]);mc[ci]=math.log1p(mass[ci])-math.log1p(mass[pi]);sc[ci]=math.log1p(strength[ci])-math.log1p(strength[pi]);rein[ci]=streak;sd4[ci]=float(np.std(centers))/max(vs[ci],STEP);cv4[ci]=float(np.std(widths)/(np.mean(widths)+EPS));pvm[ci]=prom[ci]/(histmax+EPS);states[lid]={'age':ag,'streak':streak,'centers':centers,'widths':widths,'prommax':histmax,'first':st['first'],'first_lm':st['first_lm']}
   else:
    lid=nextid;nextid+=1;lin[ci]=lid;states[lid]={'age':1,'streak':0,'centers':[center[ci]],'widths':[hi[ci]-lo[ci]],'prommax':prom[ci],'first':times[ci],'first_lm':lm}
  prev=cur
 G=Z.copy();G['lineage_id_greedy']=lin;G['age_lm']=age;G['age_active_min']=aa;G['age_civil_min']=ac;G['center_shift_vseg']=cs;G['width_log_change']=wc;G['prom_log_change']=pc;G['mass_log_change']=mc;G['strength_log_change']=sc;G['reinforce_streak']=rein;G['center_sd4_vseg']=sd4;G['width_cv4']=cv4;G['prom_vs_histmax']=pvm;G['greedy_prev_link']=plink
 return G,groups

def ref_prev_links(Z,eligible):
 ref=np.full(len(Z),-1,np.int64);by={int(k):g.index.to_numpy(np.int64) for k,g in Z.groupby('landmark_i',sort=True)};prev=np.array([],dtype=np.int64)
 for lm in eligible:
  cur=by.get(int(lm),np.array([],dtype=np.int64))
  if len(cur)==0:prev=np.array([],dtype=np.int64);continue
  if len(prev):
   pm={int(Z.lineage_id.iloc[i]):int(i) for i in prev}
   for ci in cur:
    lid=int(Z.lineage_id.iloc[ci])
    if lid in pm:ref[ci]=pm[lid]
  prev=cur
 return ref

def landmark_metrics(D,a,b):
 T=pd.DataFrame({'lm':D.landmark_i.to_numpy(),'a':a,'b':b},index=D.index);sp=[];top=[];jac=[]
 for _,g in T.groupby('lm',sort=False):
  top.append(g.a.idxmax()==g.b.idxmax())
  if len(g)>=3:
   s=spearmanr(g.a,g.b).statistic
   if np.isfinite(s):sp.append(s)
   A=set(g.nlargest(3,'a').index);B=set(g.nlargest(3,'b').index);jac.append(len(A&B)/len(A|B))
 return {'within_landmark_spearman_median':float(np.median(sp)),'within_landmark_spearman_mean':float(np.mean(sp)),'top1_agreement':float(np.mean(top)),'top3_jaccard_mean':float(np.mean(jac)),'eligible_rank_landmarks':len(sp)}

def main():
 a=parse();Z=pd.read_pickle(a.pkl).reset_index(drop=True);Z['time']=pd.to_datetime(Z.time,utc=True);eligible=eligible_from_files(a.files);ref=ref_prev_links(Z,eligible);G,_=greedy_states(Z,eligible)
 F=dec(Z);G=dec(G);p=json.load(open(a.frozen_json))['feeds']['BID']['M0GL'];s0=pred(F,p);s1=pred(G,p);err=np.abs(s0-s1)
 link=float(np.mean(ref==G.greedy_prev_link.to_numpy(np.int64)))
 state_cols=['age_lm','age_active_min','age_civil_min','center_shift_vseg','width_log_change','prom_log_change','mass_log_change','strength_log_change','reinforce_streak','center_sd4_vseg','width_cv4','prom_vs_histmax'];state={}
 for c in state_cols:
  e=np.abs(Z[c].to_numpy(float)-G[c].to_numpy(float));state[c]={'exact_rate':float(np.mean(e<=1e-12)),'median_abs_error':float(np.median(e)),'p95_abs_error':float(np.quantile(e,.95)),'max_abs_error':float(np.max(e))}
 lm=landmark_metrics(Z,s0,s1);m={'rows':len(Z),'eligible_landmarks':len(eligible),'previous_link_agreement':link,'score_pearson':float(pearsonr(s0,s1).statistic),'score_spearman':float(spearmanr(s0,s1).statistic),'score_abs_error_median':float(np.median(err)),'score_abs_error_p95':float(np.quantile(err,.95)),'score_abs_error_p99':float(np.quantile(err,.99)),**lm,'state_feature_errors':state}
 ck={'previous_link_agreement_ge_0995':link>=.995,'score_pearson_ge_0999':m['score_pearson']>=.999,'score_spearman_ge_0999':m['score_spearman']>=.999,'median_score_error_le_0002':m['score_abs_error_median']<=.002,'p95_score_error_le_0020':m['score_abs_error_p95']<=.020,'within_landmark_median_spearman_ge_0999':m['within_landmark_spearman_median']>=.999,'top1_agreement_ge_0995':m['top1_agreement']>=.995,'top3_jaccard_ge_0995':m['top3_jaccard_mean']>=.995}
 out={'status':'PASS' if all(ck.values()) else 'FAIL','scope':'OUTCOME_BLIND_GREEDY_VS_HUNGARIAN_LINEAGE_ASSIGNMENT_DEV_BID','future_outcomes_used':False,'metrics':m,'checks':ck};Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
