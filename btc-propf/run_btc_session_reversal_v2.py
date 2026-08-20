#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, math
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v1', ROOT/'run_btc_session_momentum_v1.py')
v1=importlib.util.module_from_spec(spec); spec.loader.exec_module(v1)


def main():
    out=Path('btc-propf/results/session_reversal_v2'); out.mkdir(parents=True,exist_ok=True)
    try:
        d,diag=v1.load_data(out)
        ev=v1.build_events(d)
        if ev.empty: raise RuntimeError('no events')
        ev=ev.copy(); ev['side']=-ev['side']
        grid=[]; dev_trades={}
        for block in v1.BLOCKS:
            for highvol in [False,True]:
                name=f'{block}_{"HIGHVOL" if highvol else "ALL"}'
                x=v1.candidate_events(ev,block,highvol,2019,2023)
                tr=v1.simulate_frame(x,v1.COSTS['PRIMARY']); dev_trades[name]=tr
                m=v1.metrics(tr)
                eligible=(m['n']>=400 and m['mean'] is not None and m['mean']>=0.05 and m['pf'] is not None and m['pf']>=1.10
                          and m['positive_years']>=3 and m['max_dd'] is not None and m['max_dd']<=25.0)
                score=(m['mean']*math.sqrt(m['n'])) if eligible else -999.0
                grid.append({'candidate':name,'block':block,'highvol':highvol,'eligible':eligible,'score':score,
                             **{k:v for k,v in m.items() if k!='annual'}})
        gd=pd.DataFrame(grid).sort_values(['eligible','score','candidate'],ascending=[False,False,True]); gd.to_csv(out/'dev_grid.csv',index=False)
        elig=gd[gd.eligible]
        if elig.empty:
            result={'status':'BTC_SESSION_REVERSAL_V2_DEV_NO_GO','data':diag,'n_candidates':6,'n_eligible':0,'oos_2026_opened':False}
            (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2)); return
        sel=elig.iloc[0]; name=str(sel.candidate); block=str(sel.block); highvol=bool(sel.highvol)
        dev_trades[name].to_csv(out/'selected_dev_trades.csv',index=False)
        selected_dev=v1.metrics(dev_trades[name])
        freeze={'candidate':name,'block':block,'highvol':highvol,'selection_score':float(sel.score),'dev_metrics':selected_dev}
        (out/'SELECTED_PREVALIDATION.json').write_text(json.dumps(freeze,indent=2))
        xv=v1.candidate_events(ev,block,highvol,2024,2025)
        vp=v1.simulate_frame(xv,v1.COSTS['PRIMARY']); vs=v1.simulate_frame(xv,v1.COSTS['STRESS'])
        vp.to_csv(out/'validation_primary_trades.csv',index=False); vs.to_csv(out/'validation_stress_trades.csv',index=False)
        mp=v1.metrics(vp); ms=v1.metrics(vs)
        val_pass=(mp['n']>=150 and mp['mean'] is not None and mp['mean']>=0.05 and mp['pf'] is not None and mp['pf']>=1.10
                  and mp['positive_years']==2 and mp['active_years']==2 and mp['max_dd'] is not None and mp['max_dd']<=15.0
                  and ms['mean'] is not None and ms['mean']>0 and ms['pf'] is not None and ms['pf']>1.00)
        status='BTC_SESSION_REVERSAL_V2_READY_FOR_2026_OOS_FREEZE' if val_pass else 'BTC_SESSION_REVERSAL_V2_VALIDATION_NO_GO'
        result={'status':status,'data':diag,'selected':freeze,'validation_primary':mp,'validation_stress':ms,
                'validation_pass':val_pass,'oos_2026_opened':False}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
    except Exception as e:
        result={'status':'BTC_SESSION_REVERSAL_V2_INVALID_ABORT','error':repr(e),'oos_2026_opened':False}
        (out/'RESULT.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2)); raise

if __name__=='__main__': main()
