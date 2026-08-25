#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod

v01=load_module('reaction_v01',HERE/'xau_ebuy_coverage_v0_1.py')
v04=load_module('reaction_v04',HERE/'xau_ebuy_coverage_v0_4_sticky.py')

TRIGGERS=('TOUCH_REF','RECLAIM_CENTER','RECLAIM_FULL','BULL_REJECTION')
FP_SPECS=(('FP_0.50v_vs_0.25v',.50,.25),('FP_1.00v_vs_0.50v',1.00,.50),('FP_1.50v_vs_0.75v',1.50,.75))
DEV_LO=pd.Timestamp('2024-08-01T00:00:00Z');DEV_HI=pd.Timestamp('2025-08-01T00:00:00Z')


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--files',nargs='+',required=True)
    p.add_argument('--z4-pkl',required=True)
    p.add_argument('--coverage-oos-result',required=True)
    p.add_argument('--contacts-csv',required=True)
    p.add_argument('--trigger-csv',required=True)
    p.add_argument('--output',required=True)
    return p.parse_args()


def raw_index(raw,t,side='right'):
    arr=raw.time.to_numpy(dtype='datetime64[ns]');q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr,q,side=side)-1)


def active_index(active,t):
    arr=active.time.to_numpy(dtype='datetime64[ns]');q=np.datetime64(pd.Timestamp(t).tz_convert('UTC').tz_localize(None))
    return int(np.searchsorted(arr,q,side='right')-1)


def ny_end(t):
    ny=pd.Timestamp(t).tz_convert('America/New_York')
    return pd.Timestamp(year=ny.year,month=ny.month,day=ny.day,hour=17,tz='America/New_York').tz_convert('UTC')


def subperiod(t):
    ny=pd.Timestamp(t).tz_convert('America/New_York');m=ny.hour*60+ny.minute
    if 8*60<=m<9*60+30:return 'US_EARLY'
    if 9*60+30<=m<12*60:return 'US_MORNING'
    if 12*60<=m<17*60:return 'US_AFTERNOON'
    return 'NON_US'


def match(a,b,tol):return v01.overlap(a,b) or abs(a.center-b.center)<=tol


def target_map(z4,snaps):
    by={pd.Timestamp(t):g.copy() for t,g in z4.groupby('time',sort=True)};out={}
    for s in snaps:
        g=by.get(s['time']);close=s['close']
        if g is None:continue
        u=g[(g.side==1)&(g.zlo>close)]
        if len(u)==0:u=g[g.side==1]
        if len(u)==0:continue
        r=u.iloc[int(np.argmin(u.zlo.to_numpy(float)-close))]
        out[s['time']]={'center':float(r.center),'zlo':float(r.zlo),'zhi':float(r.zhi)}
    return out


def assign_episode_states(snaps,displays):
    seq=[];next_id=1;prev=[];prev_s=None
    for s,zs in zip(snaps,displays):
        cur=[];used=set();contig=prev_s is not None and s['time']-prev_s['time']==pd.Timedelta(minutes=5)
        tol=.25*max(prev_s['v'],s['v']) if contig else 0.
        for slot,z in enumerate(zs,1):
            cand=[]
            if contig:
                for j,st in enumerate(prev):
                    if j in used:continue
                    if match(st['zone'],z,tol):cand.append((abs(st['zone'].center-z.center),j,st))
            if cand:
                _,j,old=min(cand,key=lambda x:(x[0],x[1]));used.add(j)
                st={'id':old['id'],'age':old['age']+1,'zone':z,'slot':slot,'armed':old['armed'],'arm_time':old['arm_time'],'arm_close':old['arm_close'],'consumed':old['consumed'],'origin_family':old['origin_family']}
            else:
                st={'id':next_id,'age':1,'zone':z,'slot':slot,'armed':False,'arm_time':None,'arm_close':None,'consumed':False,'origin_family':z.family};next_id+=1
            cur.append(st)
        seq.append(cur);prev=cur;prev_s=s
    return seq


def trends(active,i,v):
    c=float(active.at[i,'close']);out={}
    for h in (5,15,60,240):
        j=max(0,i-h);out[f'trend{h}_v']=(c-float(active.at[j,'close']))/v
    return out


def fp_status(raw,start_idx,end_idx,entry,v,up_mult,dn_mult,touch_idx=None):
    up=entry+up_mult*v;dn=entry-dn_mult*v
    for j in range(start_idx,end_idx+1):
        hi=float(raw.at[j,'high']);lo=float(raw.at[j,'low']);u=hi>=up;d=lo<=dn
        if u and d:return 'AMBIGUOUS',j
        if u:return 'FAVORABLE_FIRST',j
        if d:return 'ADVERSE_FIRST',j
    return 'NEITHER',None


def target_invalidation_status(raw,start_idx,end_idx,tp_zlo,zlo):
    for j in range(start_idx,end_idx+1):
        tp=float(raw.at[j,'high'])>=tp_zlo;inv=float(raw.at[j,'close'])<zlo
        if tp and inv:return 'AMBIGUOUS',j,j
        if tp:return 'TP1_FIRST',j,None
        if inv:return 'INVALIDATION_FIRST',None,j
    return 'NEITHER',None,None


def find_confirmation(raw,contact_idx,end_idx,z,tp_zlo,kind):
    target_seen=False
    for j in range(contact_idx,end_idx+1):
        r=raw.loc[j];target_seen=target_seen or float(r.high)>=tp_zlo
        invalid=float(r.close)<z.zlo
        if invalid:return {'fired':False,'reason':'INVALIDATED_BEFORE_TRIGGER'}
        if kind=='RECLAIM_CENTER':cond=float(r.close)>=z.center
        elif kind=='RECLAIM_FULL':cond=float(r.close)>=z.zhi
        elif kind=='BULL_REJECTION':
            rng=float(r.high-r.low);cp=(float(r.close-r.low)/rng) if rng>0 else 0.;cond=float(r.close)>float(r.open) and cp>=.70
        else:raise ValueError(kind)
        if cond:
            if target_seen:return {'fired':False,'reason':'TARGET_ALREADY_REACHED_BEFORE_TRIGGER'}
            ex=j+1
            if ex>end_idx:return {'fired':False,'reason':'NO_NEXT_OPEN_BEFORE_US_END'}
            if pd.Timestamp(raw.at[ex,'time'])>=ny_end(raw.at[j,'time']):return {'fired':False,'reason':'NO_NEXT_OPEN_BEFORE_US_END'}
            price=float(raw.at[ex,'open'])
            if price>=tp_zlo:return {'fired':False,'reason':'TARGET_ALREADY_REACHED_BEFORE_TRIGGER'}
            return {'fired':True,'trigger_idx':j,'exec_idx':ex,'exec_price':price,'trigger_time':pd.Timestamp(raw.at[j,'time']),'exec_time':pd.Timestamp(raw.at[ex,'time'])}
    return {'fired':False,'reason':'TRIGGER_NOT_SEEN'}


def trigger_outcome(raw,contact_idx,end_idx,z,tp,v,kind):
    if kind=='TOUCH_REF':
        info={'fired':True,'trigger_idx':contact_idx,'exec_idx':contact_idx,'exec_price':float(z.zhi),'trigger_time':pd.Timestamp(raw.at[contact_idx,'time']),'exec_time':pd.Timestamp(raw.at[contact_idx,'time'])}
    else:info=find_confirmation(raw,contact_idx,end_idx,z,float(tp['zlo']),kind)
    if not info['fired']:
        return {'trigger':kind,**info}
    st=int(info['exec_idx']);entry=float(info['exec_price'])
    rec={'trigger':kind,**info,'tp_distance_v':(float(tp['zlo'])-entry)/v}
    for nm,up,dn in FP_SPECS:
        s,j=fp_status(raw,st,end_idx,entry,v,up,dn,contact_idx if kind=='TOUCH_REF' else None);rec[nm]=s;rec[nm+'_time']=str(raw.at[j,'time']) if j is not None else None
    os,tpj,invj=target_invalidation_status(raw,st,end_idx,float(tp['zlo']),float(z.zlo));rec['tp1_invalidation_status']=os
    rec['tp1_time']=str(raw.at[tpj,'time']) if tpj is not None else None;rec['invalidation_time']=str(raw.at[invj,'time']) if invj is not None else None
    h=raw.high.iloc[st:end_idx+1].to_numpy(float);l=raw.low.iloc[st:end_idx+1].to_numpy(float)
    rec['mfe_v']=float(max(0.,h.max()-entry)/v) if len(h) else 0.;rec['mae_v']=float(max(0.,entry-l.min())/v) if len(l) else 0.
    return rec


def detect_contacts(raw,active,z4,snaps,displays,states):
    targets=target_map(z4,snaps);contacts=[];trades=[]
    for i,(s,zs,sts) in enumerate(zip(snaps,displays,states)):
        if not (DEV_LO<=s['time']<DEV_HI):continue
        if s['time'] not in targets:continue
        next_boundary=s['time']+pd.Timedelta(minutes=5);end=min(next_boundary,ny_end(s['time']))
        i0=raw_index(raw,s['time'],'right')+1;i1=raw_index(raw,end-pd.Timedelta(nanoseconds=1),'right')
        if i1<i0:continue
        for z,st in zip(zs,sts):
            if st['consumed']:continue
            # A confirmed C5/M1 close can arm immediately.
            if not st['armed'] and s['close']>z.zhi:
                st['armed']=True;st['arm_time']=s['time'];st['arm_close']=s['close']
            contact_idx=None
            for j in range(i0,i1+1):
                r=raw.loc[j]
                if not st['armed']:
                    if float(r.close)>z.zhi:
                        st['armed']=True;st['arm_time']=pd.Timestamp(r.time);st['arm_close']=float(r.close)
                    continue
                if float(r.high)>=z.zlo and float(r.low)<=z.zhi:
                    contact_idx=j;break
            if contact_idx is None:continue
            st['consumed']=True
            ct=pd.Timestamp(raw.at[contact_idx,'time']);v=float(s['v']);tp=targets[s['time']]
            ai=active_index(active,ct);tr=trends(active,ai,v) if ai>=0 else {f'trend{h}_v':None for h in (5,15,60,240)}
            rr=raw.loc[contact_idx];width=max(z.zhi-z.zlo,1e-12);rng=float(rr.high-rr.low);cp=float((rr.close-rr.low)/rng) if rng>0 else 0.
            contact={
              'episode_id':st['id'],'contact_time':ct,'c5_time':s['time'],'family':z.family,'episode_origin_family':st['origin_family'],'slot_rank':st['slot'],'episode_age_c5':st['age'],
              'zlo':z.zlo,'center':z.center,'zhi':z.zhi,'zone_width_v':width/v,'v_contact':v,
              'arm_time':st['arm_time'],'arm_close':st['arm_close'],'arm_center_distance_v':((st['arm_close']-z.center)/v if st['arm_close'] is not None else None),
              'tp1_zlo':tp['zlo'],'tp1_center':tp['center'],'tp1_zhi':tp['zhi'],'tp1_distance_from_touch_ref_v':(tp['zlo']-z.zhi)/v,
              'minutes_to_us_end':(ny_end(ct)-ct).total_seconds()/60.,'us_subperiod':subperiod(ct),
              'contact_penetration_width':(z.zhi-float(rr.low))/width,'contact_bull':int(float(rr.close)>float(rr.open)),'contact_close_position':cp,
              'approach5_v':tr.get('trend5_v'),'approach15_v':tr.get('trend15_v'),**tr}
            contacts.append(contact)
            end_session=ny_end(ct);ej=raw_index(raw,end_session-pd.Timedelta(nanoseconds=1),'right')
            for kind in TRIGGERS:
                rec=trigger_outcome(raw,contact_idx,ej,z,tp,v,kind)
                trades.append({**contact,**rec})
    return contacts,trades


def fp_summary(rows,nm):
    c=pd.Series([r[nm] for r in rows if r.get('fired')]).value_counts().to_dict();fav=int(c.get('FAVORABLE_FIRST',0));adv=int(c.get('ADVERSE_FIRST',0));amb=int(c.get('AMBIGUOUS',0));nei=int(c.get('NEITHER',0));res=fav+adv
    return {'favorable_first':fav,'adverse_first':adv,'ambiguous':amb,'neither':nei,'resolved_denominator':res,'favorable_resolved_rate':float(fav/res) if res else None,'ambiguity_rate':float(amb/(fav+adv+amb+nei)) if fav+adv+amb+nei else None}


def summarize_trigger(rows,total_contacts):
    fired=[r for r in rows if r.get('fired')];reasons=pd.Series([r.get('reason') for r in rows if not r.get('fired')]).value_counts().to_dict() if rows else {}
    os=pd.Series([r.get('tp1_invalidation_status') for r in fired]).value_counts().to_dict() if fired else {}
    resolved_n=len(fired)-int(os.get('AMBIGUOUS',0));tp=int(os.get('TP1_FIRST',0));inv=int(os.get('INVALIDATION_FIRST',0));nei=int(os.get('NEITHER',0))
    def quant(field):
        a=np.asarray([float(r[field]) for r in fired if r.get(field) is not None and np.isfinite(float(r[field]))],float)
        return {'median':float(np.median(a)) if len(a) else None,'p90':float(np.quantile(a,.9)) if len(a) else None}
    out={'fired_count':len(fired),'fired_share_of_contacts':float(len(fired)/total_contacts) if total_contacts else 0.,'nonfire_reasons':{str(k):int(v) for k,v in reasons.items()},
         'tp1_invalidation':{'TP1_FIRST':tp,'INVALIDATION_FIRST':inv,'NEITHER':nei,'AMBIGUOUS':int(os.get('AMBIGUOUS',0)),'resolved_share':float(resolved_n/len(fired)) if fired else None,
                             'tp1_resolved_rate':float(tp/resolved_n) if resolved_n else None,'invalidation_resolved_rate':float(inv/resolved_n) if resolved_n else None,'neither_resolved_rate':float(nei/resolved_n) if resolved_n else None},
         'fp':{nm:fp_summary(fired,nm) for nm,_,_ in FP_SPECS},'mfe_v':quant('mfe_v'),'mae_v':quant('mae_v'),'tp_distance_v':quant('tp_distance_v'),'minutes_to_us_end':quant('minutes_to_us_end')}
    out['DEV_ELIGIBLE']=bool(len(fired)>=1000 and out['fired_share_of_contacts']>=.20 and out['tp1_invalidation']['resolved_share'] is not None and out['tp1_invalidation']['resolved_share']>=.90)
    return out


def stratified(trades,total_contacts):
    out={'by_family':{},'by_us_subperiod':{}}
    for field,key in [('family','by_family'),('us_subperiod','by_us_subperiod')]:
        vals=sorted({r[field] for r in trades})
        for val in vals:
            d={}
            contact_ids={r['episode_id'] for r in trades if r[field]==val}
            for trig in TRIGGERS:
                rr=[r for r in trades if r[field]==val and r['trigger']==trig]
                d[trig]={'sparse':len(contact_ids)<100,'contact_episode_count':len(contact_ids),'summary':summarize_trigger(rr,len(contact_ids)) if len(contact_ids)>=100 else None}
            out[key][str(val)]=d
    return out


def main():
    a=parse_args();cov=json.load(open(a.coverage_oos_result))
    if cov.get('status')!='EBUY_COVERAGE_OOS_REPLICATION_PASS':raise RuntimeError('activation condition not met: OOS coverage is not PASS')
    raw=v01.load_raw(a.files);active=v01.active_m1(raw);z4=pd.read_pickle(a.z4_pkl).copy();z4['time']=pd.to_datetime(z4.time,utc=True)
    bad=sorted(v01.FORBIDDEN & set(z4.columns));
    if bad:raise RuntimeError(f'future columns in geometry: {bad}')
    snaps,pools=v04.build_fixed_pools(raw,active,z4);displays=v04.sticky_display(raw,snaps,pools);states=assign_episode_states(snaps,displays)
    contacts,trades=detect_contacts(raw,active,z4,snaps,displays,states)
    pd.DataFrame(contacts).to_csv(a.contacts_csv,index=False);pd.DataFrame(trades).to_csv(a.trigger_csv,index=False)
    summaries={}
    for trig in TRIGGERS:summaries[trig]=summarize_trigger([r for r in trades if r['trigger']==trig],len(contacts))
    elig=[t for t in TRIGGERS if summaries[t]['DEV_ELIGIBLE']]
    if elig:
        order={t:i for i,t in enumerate(TRIGGERS)}
        def key(t):
            s=summaries[t];tp=s['tp1_invalidation']['tp1_resolved_rate'];fp=s['fp']['FP_1.00v_vs_0.50v']['favorable_resolved_rate'];inv=s['tp1_invalidation']['invalidation_resolved_rate']
            return (-(tp if tp is not None else -1),-(fp if fp is not None else -1),(inv if inv is not None else 2),-s['fired_count'],order[t])
        selected=sorted(elig,key=key)[0]
    else:selected=None
    out={'status':'REACTION_DEV_COMPLETE' if selected else 'REACTION_DEV_NO_ELIGIBLE_TRIGGER','scope':'BUY_ONLY_EBUY_REACTION_DEV_H1','coverage_activation_status':cov['status'],
         'reaction_dev_window_utc':[str(DEV_LO),str(DEV_HI)],'reaction_holdout_opened':False,'contact_episode_count':len(contacts),'trigger_summaries':summaries,
         'selected_trigger':selected,'selection_rule':'preregistered v1.0 lexicographic rule','stratified':stratified(trades,len(contacts)),
         'authorization':('FREEZE_SELECTED_TRIGGER_AND_SCORE_SPEC_BEFORE_H2' if selected else 'KEEP_H2_CLOSED_AND_REPREREGISTER_DEV'),
         'explicit_nonclaims':['No H2 reaction result opened','No production E score','No live profitability claim','No R_US route claim']}
    Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps({'status':out['status'],'contacts':len(contacts),'selected_trigger':selected,'eligible_triggers':elig},indent=2),flush=True)

if __name__=='__main__':main()
