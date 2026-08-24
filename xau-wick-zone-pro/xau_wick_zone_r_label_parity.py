import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr

p=argparse.ArgumentParser();p.add_argument('--matched-csv',required=True);p.add_argument('--map-json',required=True);p.add_argument('--output',required=True);a=p.parse_args()
M=pd.read_csv(a.matched_csv);mp=json.load(open(a.map_json));T=np.array([x['raw_threshold'] for x in mp['percentile_thresholds']],float)

def rfloat(x):
 x=np.asarray(x,float);out=np.zeros(len(x),float);out[x>=T[-1]]=100.;mid=(x>T[0])&(x<T[-1]);xx=x[mid];k=np.searchsorted(T,xx,side='right')-1;k=np.clip(k,0,99);lo=T[k];hi=T[k+1];out[mid]=k+(xx-lo)/np.maximum(hi-lo,1e-20);return out

def pine_round(x):return np.floor(np.asarray(x,float)+.5).astype(int)
re=rfloat(M.score_exact.to_numpy(float));rp=rfloat(M.score_proxy.to_numpy(float));e=np.abs(re-rp);ie=np.abs(pine_round(re)-pine_round(rp))
res={'median_abs_r_float_error':float(np.median(e)),'p90_abs_r_float_error':float(np.quantile(e,.9)),'p95_abs_r_float_error':float(np.quantile(e,.95)),'p99_abs_r_float_error':float(np.quantile(e,.99)),'median_abs_display_r_error':float(np.median(ie)),'p95_abs_display_r_error':float(np.quantile(ie,.95)),'share_display_within_1':float(np.mean(ie<=1)),'share_display_within_2':float(np.mean(ie<=2)),'share_display_within_5':float(np.mean(ie<=5)),'r_pearson':float(pearsonr(re,rp).statistic),'r_spearman':float(spearmanr(re,rp).statistic),'matched_pairs':int(len(M))}
# Raw and R transforms are monotonic; use exact matched pair top-1 by landmark.
top=[]
for _,g in M.groupby('landmark_i',sort=False):
 top.append(int(g.loc[g.score_exact.idxmax(),'pidx'])==int(g.loc[g.score_proxy.idxmax(),'pidx']))
res['matched_top1_agreement']=float(np.mean(top));res['top1_landmarks']=len(top)
checks={'median_r_error_le_1':res['median_abs_r_float_error']<=1.,'p95_r_error_le_5':res['p95_abs_r_float_error']<=5.,'share_display_within2_ge_080':res['share_display_within_2']>=.80,'share_display_within5_ge_095':res['share_display_within_5']>=.95,'r_spearman_ge_098':res['r_spearman']>=.98,'top1_ge_085':res['matched_top1_agreement']>=.85}
out={'status':'PASS' if all(checks.values()) else 'FAIL','scope':'OUTCOME_BLIND_R_DISPLAY_LABEL_PARITY_DEV_BID','future_outcomes_used':False,'metrics':res,'checks':checks};Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
