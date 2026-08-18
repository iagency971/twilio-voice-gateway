#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
import build_comex_dev_rank1_event_features as feat

LEVELS=['VWAP','POC','VAH','VAL']

def main():
    ap=argparse.ArgumentParser()
    for x in ['new-root','pilot-root','requests','sessions','mapping','routing','out']:ap.add_argument('--'+x,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);newroot=Path(a.new_root);pilotroot=Path(a.pilot_root)
    req=pd.read_csv(a.requests,dtype={'symbols':str});sessions=pd.read_csv(a.sessions);sessions=sessions[sessions.acquisition_stage.eq('DEV_RANK1')].copy();mapping=pd.read_csv(a.mapping,dtype={'v0_start_iid':str,'n0_start_iid':str});routing=pd.read_csv(a.routing,dtype={'v0_iid':str,'n0_iid':str})
    assert len(sessions)==96 and len(mapping)==96 and len(routing)==96
    cand,_=feat.build_candidate_map(newroot,pilotroot,req,sessions,mapping);rt=routing.set_index(routing.research_trading_date.astype(str));rows=[];missing=[]
    for date in sorted(sessions.research_trading_date.astype(str)):
        r=rt.loc[date];leader=str(r.terminal_leader)
        if leader=='MISSING':missing.append(date);continue
        label='N0' if leader=='N0' else ('V0' if leader=='V0' else 'N0')
        z=cand.get((date,label));p=z.get('path') if z else None
        if p is None:
            # SAME may be represented on the V0 key only in a paid artifact; fallback is deterministic.
            z=cand.get((date,'V0'));p=z.get('path') if z else None
        if p is None:missing.append(date);continue
        t=feat.prep_tape(p,date)
        if t is None or len(t['price'])==0:missing.append(date);continue
        vwap,poc,vah,val=feat.profile_slice(t['price'],t['size']);s,e=feat.session_bounds(date);iid=str(z.get('iid') if z else '')
        values={'VWAP':vwap,'POC':poc,'VAH':vah,'VAL':val}
        for name,val0 in values.items():
            rows.append({'source_research_date':date,'source_session_start_utc':s.isoformat(),'known_time_utc':e.isoformat(),'terminal_leader':leader,'source_candidate_key':label,'source_instrument_id':iid,'level_type':name,'level_price':float(val0),'tick_price':float(round(float(val0)*10)/10) if name!='VWAP' else float(val0),'primary_static_level':True})
    q=pd.DataFrame(rows);q.to_csv(out/'native_source_levels.csv',index=False)
    sm={'version':'COMEX_DEV_RANK1_NATIVE_SOURCE_LEVELS_V1','market_data_api_calls':False,'analytical_sessions':96,'source_sessions_with_primary_levels':int(q.source_research_date.nunique()) if len(q) else 0,'missing_source_sessions':missing,'levels_per_source':4,'levels_total':int(len(q)),'level_types':LEVELS,'contact_rule':'future primary contact requires first exact GC trade at level tick in next auction session on same raw instrument; no M1 crossing substitution','hvn_lvn_status':'not instantiated here; secondary definitions retained but local-extrema tie convention not expanded post-acquisition','outcomes_used_to_create_levels':False}
    (out/'native_source_manifest.json').write_text(json.dumps(sm,indent=2));print(json.dumps(sm,indent=2))
if __name__=='__main__':main()
