import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import pearsonr,spearmanr

STRICT={
 'exact_match_ge_090':.90,
 'proxy_match_ge_090':.90,
 'median_iou_ge_080':.80,
 'p10_iou_ge_055':.55,
 'median_center_err_le_008':.08,
 'p95_center_err_le_025':.25,
 'score_pearson_ge_098':.98,
 'score_spearman_ge_098':.98,
 'median_score_err_le_0015':.015,
 'p95_score_err_le_0060':.060,
 'top1_agreement_ge_085':.85,
}

def parse():
 p=argparse.ArgumentParser();p.add_argument('--exact-pkl',required=True);p.add_argument('--proxy-pkl',required=True);p.add_argument('--frozen-json',required=True);p.add_argument('--output',required=True);return p.parse_args()

def decorate(D):
 D=D.copy();D['time']=pd.to_datetime(D.time,utc=True)
 D['log_age_active']=np.log1p(D.age_active_min);D['log_age_civil']=np.log1p(D.age_civil_min)
 for out,col in [('log_prom','prominence'),('log_bg','background'),('log_strength','strength_raw'),('log_mass','mass'),('log_peak','peak_height'),('log_mean_wick','mean_wick'),('log_mean_body','mean_body')]:D[out]=np.log1p(D[col])
 return D

def sigmoid(x):
 x=np.asarray(x,float);o=np.empty_like(x);m=x>=0;o[m]=1/(1+np.exp(-x[m]));e=np.exp(x[~m]);o[~m]=e/(1+e);return o

def predict(D,p):
 X=D[p['features']].to_numpy(float);mu=np.asarray(p['scaler_mean'],float);sd=np.asarray(p['scaler_scale'],float);c=np.asarray(p['coef'],float)
 if not np.isfinite(X).all():raise RuntimeError('non-finite features')
 return sigmoid(float(p['intercept'])+((X-mu)/sd)@c)

def iou_scalar(a0,a1,b0,b1):
 inter=max(0.,min(a1,b1)-max(a0,b0));union=max(a1,b1)-min(a0,b0);return inter/union if union>0 else 0.

def q(x,vals):
 a=np.asarray(x,float);return {str(v):(float(np.quantile(a,v)) if len(a) else None) for v in vals}

def match_slow(ei,pi,ec,elo,ehi,ev,pc,plo,phi,pv):
 cost=np.full((len(ei),len(pi)),1e9,float);valid=np.zeros_like(cost,dtype=bool)
 for r,eidx in enumerate(ei):
  ew=max(float(ehi[eidx]-elo[eidx]),.01)
  for c,pidx in enumerate(pi):
   pw=max(float(phi[pidx]-plo[pidx]),.01);vs=max(float(ev[eidx]),float(pv[pidx]),.01);cd=abs(float(ec[eidx]-pc[pidx]));ov=iou_scalar(float(elo[eidx]),float(ehi[eidx]),float(plo[pidx]),float(phi[pidx]));ok=(cd<=vs) or (ov>0)
   if ok:valid[r,c]=True;cost[r,c]=cd/vs+.5*(1-ov)+.1*abs(math.log(pw/ew))
 rr,cc=linear_sum_assignment(cost);return [(int(ei[r]),int(pi[c])) for r,c in zip(rr,cc) if valid[r,c] and cost[r,c]<1e8]

def match_fast(ei,pi,ec,elo,ehi,ev,pc,plo,phi,pv):
 ei=np.asarray(ei,np.int64);pi=np.asarray(pi,np.int64)
 EW=np.maximum((ehi[ei]-elo[ei])[:,None],.01);PW=np.maximum((phi[pi]-plo[pi])[None,:],.01)
 VS=np.maximum(np.maximum(ev[ei][:,None],pv[pi][None,:]),.01);CD=np.abs(ec[ei][:,None]-pc[pi][None,:])
 INTER=np.maximum(0.,np.minimum(ehi[ei][:,None],phi[pi][None,:])-np.maximum(elo[ei][:,None],plo[pi][None,:]));UNION=np.maximum(ehi[ei][:,None],phi[pi][None,:])-np.minimum(elo[ei][:,None],plo[pi][None,:]);OV=np.divide(INTER,UNION,out=np.zeros_like(INTER),where=UNION>0)
 valid=(CD<=VS)|(OV>0);cost=CD/VS+.5*(1-OV)+.1*np.abs(np.log(PW/EW));cost=np.where(valid,cost,1e9)
 rr,cc=linear_sum_assignment(cost);return [(int(ei[r]),int(pi[c])) for r,c in zip(rr,cc) if valid[r,c] and cost[r,c]<1e8]

def group_rank_metrics_fast(M):
 if not len(M):return {'within_landmark_spearman_median':None,'within_landmark_spearman_mean':None,'within_landmark_rank_landmarks':0}
 T=M[['landmark_i','score_exact','score_proxy']].copy();G=T.groupby('landmark_i',sort=False)
 T['rx']=G.score_exact.rank(method='average');T['ry']=G.score_proxy.rank(method='average');T['rx2']=T.rx*T.rx;T['ry2']=T.ry*T.ry;T['rxy']=T.rx*T.ry
 S=T.groupby('landmark_i',sort=False).agg(n=('rx','size'),sx=('rx','sum'),sy=('ry','sum'),sxx=('rx2','sum'),syy=('ry2','sum'),sxy=('rxy','sum'))
 n=S.n.to_numpy(float);sx=S.sx.to_numpy(float);sy=S.sy.to_numpy(float);vx=n*S.sxx.to_numpy(float)-sx*sx;vy=n*S.syy.to_numpy(float)-sy*sy;num=n*S.sxy.to_numpy(float)-sx*sy;den=np.sqrt(np.maximum(vx,0)*np.maximum(vy,0));rho=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0);keep=(n>=3)&np.isfinite(rho);r=rho[keep]
 return {'within_landmark_spearman_median':float(np.median(r)) if len(r) else None,'within_landmark_spearman_mean':float(np.mean(r)) if len(r) else None,'within_landmark_rank_landmarks':int(len(r))}

def subset_equivalence(E_groups,P_groups,keys,arrays):
 ec,elo,ehi,ev,pc,plo,phi,pv=arrays;checked=0
 for key in keys:
  ei=E_groups.get(key,np.array([],dtype=np.int64));pi=P_groups.get(key,np.array([],dtype=np.int64))
  if not len(ei) or not len(pi):continue
  s=match_slow(ei,pi,ec,elo,ehi,ev,pc,plo,phi,pv);f=match_fast(ei,pi,ec,elo,ehi,ev,pc,plo,phi,pv)
  assert s==f,(key,s,f);checked+=1
  if checked>=1000:break
 assert checked>=100
 return {'status':'PASS','nonempty_landmark_side_groups_checked':checked,'criterion':'identical ordered (exact_idx,proxy_idx) Hungarian matches'}

def main():
 a=parse();E=decorate(pd.read_pickle(a.exact_pkl)).reset_index(drop=True);P=decorate(pd.read_pickle(a.proxy_pkl)).reset_index(drop=True);params=json.load(open(a.frozen_json))['feeds']['BID']['M0GL'];E['score_raw']=predict(E,params);P['score_raw']=predict(P,params)
 forbidden={'revisited','touch_idx','touch_us','first_state','peak_touch','sweep_far','reclaim_peak','reclaim_full','pos5','pos15','pos30','pos60','mfe5_v','mfe15_v','mfe30_v','mfe60_v','mae5_v','mae15_v','mae30_v','mae60_v'};used={'landmark_i','side','center','zlo','zhi','vseg','score_raw'}
 if forbidden&used:raise RuntimeError('future outcome entered comparator')
 Eg={(int(lm),int(side)):g.index.to_numpy(np.int64) for (lm,side),g in E.groupby(['landmark_i','side'],sort=True)};Pg={(int(lm),int(side)):g.index.to_numpy(np.int64) for (lm,side),g in P.groupby(['landmark_i','side'],sort=True)};keys=sorted(set(Eg)|set(Pg))
 ec=E.center.to_numpy(float);elo=E.zlo.to_numpy(float);ehi=E.zhi.to_numpy(float);ev=E.vseg.to_numpy(float);pc=P.center.to_numpy(float);plo=P.zlo.to_numpy(float);phi=P.zhi.to_numpy(float);pv=P.vseg.to_numpy(float);se=E.score_raw.to_numpy(float);sp=P.score_raw.to_numpy(float);arrays=(ec,elo,ehi,ev,pc,plo,phi,pv)
 eq=subset_equivalence(Eg,Pg,keys,arrays)
 rec=[];me=set();mp=set()
 for key in keys:
  ei=Eg.get(key,np.array([],dtype=np.int64));pi=Pg.get(key,np.array([],dtype=np.int64))
  if not len(ei) or not len(pi):continue
  for eidx,pidx in match_fast(ei,pi,*arrays):
   vs=max(ev[eidx],pv[pidx],.01);ov=iou_scalar(elo[eidx],ehi[eidx],plo[pidx],phi[pidx]);rec.append((key[0],key[1],eidx,pidx,ov,abs(ec[eidx]-pc[pidx])/vs,abs(elo[eidx]-plo[pidx])/vs,abs(ehi[eidx]-phi[pidx])/vs,se[eidx],sp[pidx],abs(se[eidx]-sp[pidx])));me.add(eidx);mp.add(pidx)
 M=pd.DataFrame(rec,columns=['landmark_i','side','eidx','pidx','iou','center_err_vseg','lo_err_vseg','hi_err_vseg','score_exact','score_proxy','score_abs_err']);assert len(M)>=100
 Ec=E.groupby('landmark_i',sort=True).size();Pc=P.groupby('landmark_i',sort=True).size();lms=Ec.index.union(Pc.index);ee=Ec.reindex(lms,fill_value=0).to_numpy();pp=Pc.reindex(lms,fill_value=0).to_numpy();same=(ee==pp);cad=np.abs(ee-pp)
 pear=float(pearsonr(M.score_exact,M.score_proxy).statistic);spear=float(spearmanr(M.score_exact,M.score_proxy).statistic);rank=group_rank_metrics_fast(M)
 et=E.groupby('landmark_i',sort=True).score_raw.idxmax();pt=P.groupby('landmark_i',sort=True).score_raw.idxmax();common=et.index.intersection(pt.index);pair=pd.Series(M.pidx.to_numpy(np.int64),index=pd.MultiIndex.from_arrays([M.landmark_i.to_numpy(np.int64),M.eidx.to_numpy(np.int64)]));want=pd.MultiIndex.from_arrays([common.to_numpy(np.int64),et.loc[common].to_numpy(np.int64)]);mapped=pair.reindex(want).fillna(-1).to_numpy(np.int64);top=float(np.mean(mapped==pt.loc[common].to_numpy(np.int64)))
 metrics={'exact_rows':int(len(E)),'proxy_rows':int(len(P)),'matched_pairs':int(len(M)),'exact_zone_match_rate':float(len(me)/len(E)),'proxy_zone_match_rate':float(len(mp)/len(P)),'landmarks_exact':int(E.landmark_i.nunique()),'landmarks_proxy':int(P.landmark_i.nunique()),'same_zone_count_landmark_rate':float(np.mean(same)),'mean_abs_zone_count_difference':float(np.mean(cad)),'iou_quantiles':q(M.iou,(.1,.25,.5,.75,.9,.95)),'center_err_vseg_quantiles':q(M.center_err_vseg,(.5,.9,.95,.99)),'lo_err_vseg_quantiles':q(M.lo_err_vseg,(.5,.9,.95)),'hi_err_vseg_quantiles':q(M.hi_err_vseg,(.5,.9,.95)),'score_pearson':pear,'score_spearman':spear,'score_abs_err_quantiles':q(M.score_abs_err,(.5,.9,.95,.99)),**rank,'top1_zone_agreement':top,'top1_eligible_landmarks':int(len(common))}
 ck={'exact_match_ge_090':metrics['exact_zone_match_rate']>=.90,'proxy_match_ge_090':metrics['proxy_zone_match_rate']>=.90,'median_iou_ge_080':metrics['iou_quantiles']['0.5']>=.80,'p10_iou_ge_055':metrics['iou_quantiles']['0.1']>=.55,'median_center_err_le_008':metrics['center_err_vseg_quantiles']['0.5']<=.08,'p95_center_err_le_025':metrics['center_err_vseg_quantiles']['0.95']<=.25,'score_pearson_ge_098':metrics['score_pearson']>=.98,'score_spearman_ge_098':metrics['score_spearman']>=.98,'median_score_err_le_0015':metrics['score_abs_err_quantiles']['0.5']<=.015,'p95_score_err_le_0060':metrics['score_abs_err_quantiles']['0.95']<=.060,'top1_agreement_ge_085':metrics['top1_zone_agreement']>=.85}
 out={'status':'PASS' if all(ck.values()) else 'FAIL','parity_scope':'OUTCOME_BLIND_STRICT_C15_EQUIVALENT_COMBINED_PINE_Z4_PROXY_DEV_BID','reference':'C5 Z4 exact 0.01 / SciPy Gaussian / exact lineage state','proxy':'C5 0.05 + 3-box + explicit peaks/P50 + greedy lineage + selected C5 cap','future_outcomes_used_in_metrics':False,'strict_threshold_source':'historical C15 accepted combined parity gate','strict_thresholds':STRICT,'fast_vs_original_matching_subset_equivalence':eq,'metrics':metrics,'checks':ck};Path(a.output).write_text(json.dumps(out,indent=2));M.to_csv(Path(a.output).with_suffix('.matched.csv'),index=False);print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
