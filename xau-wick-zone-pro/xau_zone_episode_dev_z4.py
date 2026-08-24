import argparse, glob, math, warnings, json, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences, peak_widths
from scipy.optimize import linear_sum_assignment
warnings.filterwarnings('ignore')

STEP=.01; LOOKBACK=1440; HORIZON=240; REACT_MAX=60; EPS=1e-9

def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--files', nargs='+', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--tag', default='Z4')
    return p.parse_args()

def utc_ts(t):
    p=pd.Timestamp(t)
    return p.tz_localize('UTC') if p.tzinfo is None else p.tz_convert('UTC')

def session_code(ts):
    p=utc_ts(ts).tz_convert('America/New_York'); h=p.hour+p.minute/60
    if 18<=h or h<3: return 'OVERNIGHT'
    if 3<=h<8: return 'LONDON_PRE_US'
    if 8<=h<17: return 'US'
    return 'ROLLOVER'

def sub_us(ts):
    p=utc_ts(ts).tz_convert('America/New_York'); h=p.hour+p.minute/60
    if 8<=h<9.5: return 'US_EARLY'
    if 9.5<=h<12: return 'US_MORNING'
    if 12<=h<17: return 'US_AFTERNOON'
    return 'NON_US'

def landmark_ok(ts):
    p=utc_ts(ts); return p.minute%15==0 and p.second==0

def main():
    args=parse(); t0=time.time()
    frames=[]
    for pat in args.files:
        for f in sorted(glob.glob(pat)):
            d=pd.read_csv(f); d['time']=pd.to_datetime(d.timestamp,unit='ms',utc=True)
            frames.append(d[['time','open','high','low','close']])
    if not frames: raise SystemExit('No input files')
    df=pd.concat(frames,ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    a=df[df.high>df.low].reset_index(drop=True)
    O=a.open.to_numpy(float); H=a.high.to_numpy(float); L=a.low.to_numpy(float); C=a.close.to_numpy(float); T=a.time.to_numpy(); N=len(a)
    bodylo=np.minimum(O,C); bodyhi=np.maximum(O,C)
    prev=np.r_[C[0],C[:-1]]; TR=np.maximum(H-L,np.maximum(abs(H-prev),abs(L-prev)))
    v60=pd.Series(TR).rolling(60,min_periods=20).median().to_numpy()
    vseg=pd.Series(TR).rolling(LOOKBACK,min_periods=240).median().to_numpy()
    rhi=pd.Series(H).rolling(LOOKBACK,min_periods=1).max().to_numpy(); rlo=pd.Series(L).rolling(LOOKBACK,min_periods=1).min().to_numpy()
    base=0.0; maxp=math.ceil(H.max()/STEP)*STEP; nlevels=int(round(maxp/STEP))+16
    print(args.tag,'active',N,'grid',nlevels,flush=True)

    def ci(x): return np.ceil((x-base)/STEP-EPS).astype(np.int64)
    def fi(x): return np.floor((x-base)/STEP+EPS).astype(np.int64)
    ls=ci(L); le=ci(bodylo)-1; bs=ci(bodylo); be=fi(bodyhi); us=fi(bodyhi)+1; ue=fi(H)
    for x in (ls,bs,us): np.clip(x,0,nlevels-1,out=x)
    for x in (le,be,ue): np.clip(x,-1,nlevels-1,out=x)
    dL=np.zeros(nlevels+1,np.int32); dB=np.zeros_like(dL); dU=np.zeros_like(dL)
    def upd(d,s,e,delta):
        if s<=e:
            d[s]+=delta
            if e+1<len(d): d[e+1]-=delta

    def zone_detect(wick, vs, lo_idx, hi_idx):
        # Z4 outcome-blind causal repairs: fixed absolute grid origin, exact
        # active age, and no lineage bridging across a missing eligible snapshot.
        x=wick[lo_idx:hi_idx+1].astype(float)
        if len(x)<5 or not np.isfinite(vs) or vs<=0: return []
        sf=max(.25*vs/STEP,.5); sm=max(.50*vs/STEP,.5); sc=max(1.0*vs/STEP,.5)
        fine=gaussian_filter1d(x,sf,mode='nearest',truncate=4.0)
        med=gaussian_filter1d(x,sm,mode='nearest',truncate=4.0)
        coarse=gaussian_filter1d(x,sc,mode='nearest',truncate=4.0)
        fp,_=find_peaks(fine); mp,_=find_peaks(med); cp,_=find_peaks(coarse); mins,_=find_peaks(-coarse)
        if not len(cp) or not len(mp) or not len(fp): return []
        out=[]; used=set(); tol=max(1,int(round(.5*vs/STEP)))
        for c in cp:
            lc=mins[mins<c]; rc=mins[mins>c]
            bl=int(lc[-1]) if len(lc) else 0; br=int(rc[0]) if len(rc) else len(x)-1
            mps=mp[(mp>=bl)&(mp<=br)]
            if not len(mps): continue
            m=int(mps[np.argmax(med[mps])])
            if m in used or np.min(np.abs(fp-m))>tol: continue
            used.add(m)
            prom,lb,rb=peak_prominences(med,np.array([m])); prom=float(prom[0]); lb=int(lb[0]); rb=int(rb[0])
            if prom<=0: continue
            widths,heights,left_ips,right_ips=peak_widths(med,np.array([m]),rel_height=.5,prominence_data=(np.array([prom]),np.array([lb]),np.array([rb])))
            bg=float(med[m]-prom); peak=float(med[m]); strength=prom/math.sqrt(max(bg+1,1)); mass=float(np.maximum(med[lb:rb+1]-bg,0).sum()*STEP)
            gi=lo_idx+m; center=base+gi*STEP; zlo=base+(lo_idx+float(left_ips[0]))*STEP; zhi=base+(lo_idx+float(right_ips[0]))*STEP
            out.append((center,zlo,zhi,prom,bg,strength,mass,gi,lo_idx+lb,lo_idx+rb))
        return out

    def outcome_zone(i,zlo,zhi,center,side,v):
        futL=L[i+1:i+1+HORIZON]; futH=H[i+1:i+1+HORIZON]
        touch=(futH>=zlo)&(futL<=zhi)
        if not touch.any():
            return {'revisited':0,'touch_idx':-1,'touch_us':0,'time_to_touch_min':np.nan}
        pos=int(np.argmax(touch)); j=i+1+pos
        peak_touch=(L[j]<=center<=H[j])
        state=0
        if peak_touch:
            if bodylo[j]<=center<=bodyhi[j]: state=2
            elif side>0: state=1 if center>bodyhi[j] else 3
            else: state=1 if center<bodylo[j] else 3
        out={'revisited':1,'touch_idx':j,'touch_us':int(session_code(T[j])=='US'),'touch_session':session_code(T[j]),'touch_us_sub':sub_us(T[j]),
             'time_to_touch_min':j-i,'peak_touch':int(peak_touch),'first_state':state}
        for h in (5,15,30,60):
            end=min(N,j+h+1); wh=H[j:end]; wl=L[j:end]
            if side<0:
                fav=max(0.,float(wh.max()-zhi)); mae=max(0.,float(zhi-wl.min())); far=max(0.,float(zlo-wl.min()))
            else:
                fav=max(0.,float(zlo-wl.min())); mae=max(0.,float(wh.max()-zlo)); far=max(0.,float(wh.max()-zhi))
            out[f'mfe{h}_v']=fav/v; out[f'mae{h}_v']=mae/v; out[f'violation{h}_v']=far/v
            out[f'dir{h}']=(fav-far)/(fav+far+1e-9); out[f'pos{h}']=int(fav>far)
        end=min(N,j+61); lows=L[j:end]; highs=H[j:end]; closes=C[j:end]
        if side<0: broken=np.where(lows<zlo-EPS)[0]
        else: broken=np.where(highs>zhi+EPS)[0]
        out['sweep_far']=int(len(broken)>0); out['sweep_min']=float(broken[0]) if len(broken) else np.nan
        for nm in ['reclaim_far','reclaim_peak','reclaim_full','retest_zone_after_peak','retest_peak_after_peak','retest_zone_after_full','retest_peak_after_full']:
            out[nm]=0
        for nm in ['reclaim_far_min','reclaim_peak_min','reclaim_full_min','retest_zone_after_peak_min','retest_peak_after_peak_min','retest_zone_after_full_min','retest_peak_after_full_min']:
            out[nm]=np.nan
        if len(broken):
            b=int(broken[0])
            if side<0:
                cond_far=closes[b:]>=zlo; cond_peak=closes[b:]>=center; cond_full=closes[b:]>=zhi
            else:
                cond_far=closes[b:]<=zhi; cond_peak=closes[b:]<=center; cond_full=closes[b:]<=zlo
            reclaim_positions={}
            for name,cond in [('far',cond_far),('peak',cond_peak),('full',cond_full)]:
                rr=np.where(cond)[0]
                if len(rr):
                    rp=b+int(rr[0]); reclaim_positions[name]=rp
                    out[f'reclaim_{name}']=1; out[f'reclaim_{name}_min']=float(rp)
            def retest_after(rp, suffix):
                start=rp+1
                if start>=len(lows): return
                tz=(highs[start:]>=zlo)&(lows[start:]<=zhi)
                tp=(highs[start:]>=center)&(lows[start:]<=center)
                if tz.any():
                    q=start+int(np.argmax(tz)); out[f'retest_zone_after_{suffix}']=1; out[f'retest_zone_after_{suffix}_min']=float(q)
                if tp.any():
                    q=start+int(np.argmax(tp)); out[f'retest_peak_after_{suffix}']=1; out[f'retest_peak_after_{suffix}_min']=float(q)
            if 'peak' in reclaim_positions: retest_after(reclaim_positions['peak'],'peak')
            if 'full' in reclaim_positions: retest_after(reclaim_positions['full'],'full')
        out['sweep_reclaim_peak']=int(out['sweep_far'] and out['reclaim_peak'])
        out['sweep_reclaim_full']=int(out['sweep_far'] and out['reclaim_full'])
        out['sweep_reclaim_full_retest_zone']=int(out['sweep_far'] and out['reclaim_full'] and out['retest_zone_after_full'])
        out['sweep_reclaim_full_retest_peak']=int(out['sweep_far'] and out['reclaim_full'] and out['retest_peak_after_full'])
        return out

    rows=[]; landmarks=0; zone_counts=[]; eligible_landmarks=[]
    for i in range(N):
        upd(dL,int(ls[i]),int(le[i]),1); upd(dB,int(bs[i]),int(be[i]),1); upd(dU,int(us[i]),int(ue[i]),1)
        old=i-LOOKBACK
        if old>=0:
            upd(dL,int(ls[old]),int(le[old]),-1); upd(dB,int(bs[old]),int(be[old]),-1); upd(dU,int(us[old]),int(ue[old]),-1)
        if i<LOOKBACK-1 or i+HORIZON+REACT_MAX>=N or not landmark_ok(T[i]): continue
        eligible_landmarks.append(i)
        v=v60[i]; vs=vseg[i]
        if not np.isfinite(v) or v<=0 or not np.isfinite(vs) or vs<=0: continue
        cntL=np.cumsum(dL[:-1],dtype=np.int32); cntB=np.cumsum(dB[:-1],dtype=np.int32); cntU=np.cumsum(dU[:-1],dtype=np.int32); wick=cntL+cntU
        ilo=max(0,int(math.floor((rlo[i]-base)/STEP))-5); ihi=min(nlevels-1,int(math.ceil((rhi[i]-base)/STEP))+5)
        zones=zone_detect(wick,vs,ilo,ihi); zone_counts.append(len(zones)); landmarks+=1
        close=C[i]; pny=utc_ts(T[i]).tz_convert('America/New_York'); mow=pny.weekday()*1440+pny.hour*60+pny.minute; ang=2*np.pi*mow/(7*1440)
        trend15=(close-C[max(0,i-15)])/v; trend60=(close-C[max(0,i-60)])/v; trend240=(close-C[max(0,i-240)])/v
        for center,zlo,zhi,prom,bg,strength,mass,gi,lb,rb in zones:
            if zhi < close-STEP*.5: side=-1
            elif zlo > close+STEP*.5: side=1
            else: continue
            width=zhi-zlo; dist=(center-close)/v
            exp_center=float(cntL[gi]+cntB[gi]+cntU[gi]); same_center=float(cntL[gi] if side<0 else cntU[gi]); body_center=float(cntB[gi])
            zl=max(0,int(math.floor((zlo-base)/STEP))); zh=min(nlevels-1,int(math.ceil((zhi-base)/STEP)))
            mean_wick=float(wick[zl:zh+1].mean()); mean_body=float(cntB[zl:zh+1].mean()); mean_exp=mean_wick+mean_body
            out=outcome_zone(i,zlo,zhi,center,side,v)
            rec={'time':utc_ts(T[i]),'landmark_i':i,'center':center,'zlo':zlo,'zhi':zhi,'side':side,'dist_v':dist,'absdist_v':abs(dist),'width_v':width/v,
                 'tr':v,'vseg':vs,'width_vseg':width/vs,'trend15':trend15,'trend60':trend60,'trend240':trend240,'week_sin':np.sin(ang),'week_cos':np.cos(ang),
                 'landmark_session':session_code(T[i]),'landmark_us':int(session_code(T[i])=='US'),
                 'prominence':prom,'background':bg,'strength_raw':strength,'mass':mass,'peak_height':prom+bg,
                 'log_exposure_center':np.log1p(exp_center),'same_share_center':(same_center+.5)/(exp_center+1.5),'same_minus_body_center':np.log1p(same_center)-np.log1p(body_center),
                 'mean_wick':mean_wick,'mean_body':mean_body,'mean_exposure':mean_exp,'wick_share_zone':(mean_wick+.5)/(mean_exp+1.0)}
            rec.update(out); rows.append(rec)
        if landmarks%500==0: print(args.tag,'landmarks',landmarks,'rows',len(rows),'time',utc_ts(T[i]),'last500 mean zones',round(float(np.mean(zone_counts[-500:])),2),flush=True)
    Z=pd.DataFrame(rows).reset_index(drop=True)
    print(args.tag,'base dataset',len(Z),'landmarks',Z.landmark_i.nunique(),'counts q',np.quantile(zone_counts,[0,.5,.9,.95,.99,1]),flush=True)

    m=len(Z)
    lineage_id=np.zeros(m,np.int64); age_lm=np.ones(m,np.int64); age_active=np.zeros(m,float); age_civil=np.zeros(m)
    center_shift=np.zeros(m); width_change=np.zeros(m); prom_change=np.zeros(m); mass_change=np.zeros(m); strength_change=np.zeros(m)
    reinforce=np.zeros(m,np.int64); center_sd4=np.zeros(m); width_cv4=np.zeros(m); prom_vs_max=np.ones(m)
    centers_all=Z.center.to_numpy(float); zlo_all=Z.zlo.to_numpy(float); zhi_all=Z.zhi.to_numpy(float); vseg_all=Z.vseg.to_numpy(float)
    prom_all=Z.prominence.to_numpy(float); mass_all=Z.mass.to_numpy(float); strength_all=Z.strength_raw.to_numpy(float); times_all=Z.time.to_numpy()
    by_landmark={int(k):g.index.to_numpy(np.int64) for k,g in Z.groupby('landmark_i',sort=True)}
    groups=[by_landmark.get(int(lm),np.array([],dtype=np.int64)) for lm in eligible_landmarks]
    next_id=1; prev_idx=np.array([],dtype=np.int64); states={}
    for gi,(cur_landmark_i,cur_idx) in enumerate(zip(eligible_landmarks,groups)):
        cur_landmark_i=int(cur_landmark_i)
        if len(cur_idx)==0:
            prev_idx=np.array([],dtype=np.int64)
            continue
        assignments={}
        if len(prev_idx) and len(cur_idx):
            cost=np.full((len(prev_idx),len(cur_idx)),1e6,float); valid=np.zeros_like(cost,dtype=bool)
            for r,pi in enumerate(prev_idx):
                pw=max(zhi_all[pi]-zlo_all[pi],STEP)
                for c,ci_ in enumerate(cur_idx):
                    cw=max(zhi_all[ci_]-zlo_all[ci_],STEP); cd=abs(centers_all[pi]-centers_all[ci_]); vs=max(vseg_all[pi],vseg_all[ci_],STEP)
                    inter=max(0.,min(zhi_all[pi],zhi_all[ci_])-max(zlo_all[pi],zlo_all[ci_])); union=max(zhi_all[pi],zhi_all[ci_])-min(zlo_all[pi],zlo_all[ci_]); iou=inter/union if union>0 else 0
                    ok=(cd<=vs) or (iou>0)
                    if ok:
                        valid[r,c]=True; cost[r,c]=cd/vs + .5*(1-iou) + .1*abs(math.log(cw/pw))
            rr,cc=linear_sum_assignment(cost)
            for r,c in zip(rr,cc):
                if valid[r,c] and cost[r,c]<1e5: assignments[int(cur_idx[c])]=int(prev_idx[r])
        for ci_ in cur_idx:
            ci_=int(ci_)
            if ci_ in assignments:
                pi=assignments[ci_]; lid=int(lineage_id[pi]); st=states[lid]
                age=st['age']+1; streak=st['streak']+1 if prom_all[ci_]>prom_all[pi] else 0
                centers=(st['centers']+[centers_all[ci_]])[-4:]; widths=(st['widths']+[zhi_all[ci_]-zlo_all[ci_]])[-4:]
                first=st['first']; histmax=max(st['prommax'],prom_all[ci_])
                lineage_id[ci_]=lid; age_lm[ci_]=age
                age_active[ci_]=float(cur_landmark_i-st['first_landmark_i'])
                age_civil[ci_]=(pd.Timestamp(times_all[ci_])-pd.Timestamp(first)).total_seconds()/60
                center_shift[ci_]=abs(centers_all[ci_]-centers_all[pi])/max(vseg_all[ci_],STEP)
                width_change[ci_]=math.log(max(zhi_all[ci_]-zlo_all[ci_],STEP)/max(zhi_all[pi]-zlo_all[pi],STEP))
                prom_change[ci_]=math.log1p(prom_all[ci_])-math.log1p(prom_all[pi]); mass_change[ci_]=math.log1p(mass_all[ci_])-math.log1p(mass_all[pi]); strength_change[ci_]=math.log1p(strength_all[ci_])-math.log1p(strength_all[pi])
                reinforce[ci_]=streak; center_sd4[ci_]=float(np.std(centers))/max(vseg_all[ci_],STEP); width_cv4[ci_]=float(np.std(widths)/(np.mean(widths)+EPS)); prom_vs_max[ci_]=prom_all[ci_]/(histmax+EPS)
                states[lid]={'age':age,'streak':streak,'centers':centers,'widths':widths,'prommax':histmax,'first':first,'first_landmark_i':st['first_landmark_i']}
            else:
                lid=next_id; next_id+=1; lineage_id[ci_]=lid
                states[lid]={'age':1,'streak':0,'centers':[centers_all[ci_]],'widths':[zhi_all[ci_]-zlo_all[ci_]],'prommax':prom_all[ci_],'first':times_all[ci_],'first_landmark_i':cur_landmark_i}
        prev_idx=cur_idx
        if (gi+1)%2000==0: print(args.tag,'lineage',gi+1,'/',len(groups),flush=True)
    Z['lineage_id']=lineage_id; Z['age_lm']=age_lm; Z['age_active_min']=age_active; Z['age_civil_min']=age_civil
    Z['center_shift_vseg']=center_shift; Z['width_log_change']=width_change; Z['prom_log_change']=prom_change; Z['mass_log_change']=mass_change; Z['strength_log_change']=strength_change
    Z['reinforce_streak']=reinforce; Z['center_sd4_vseg']=center_sd4; Z['width_cv4']=width_cv4; Z['prom_vs_histmax']=prom_vs_max
    Z.to_pickle(args.output)
    summ={'tag':args.tag,'rows':len(Z),'landmarks':int(Z.landmark_i.nunique()),'eligible_landmarks':int(len(eligible_landmarks)),
          'missing_side_zone_landmarks':int(len(eligible_landmarks)-Z.landmark_i.nunique()),'lineages':int(Z.lineage_id.nunique()),
          'zone_count_quantiles':{str(q):float(np.quantile(zone_counts,q)) for q in [0,.5,.9,.95,.99,1]},
          'age_lm_quantiles':{str(q):float(Z.age_lm.quantile(q)) for q in [.5,.75,.9,.95,.99]},
          'revisit_rate':float(Z.revisited.mean()),'runtime_sec':time.time()-t0}
    Path(str(args.output).replace('.pkl','_summary.json')).write_text(json.dumps(summ,indent=2))
    print(json.dumps(summ,indent=2),flush=True)

if __name__=='__main__': main()
