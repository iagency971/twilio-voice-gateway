#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
import databento as db

SIDE_NONE={'N','None','nan','NaN','','0'}; EPS=1e-9

def load(p): return db.DBNStore.from_file(p).to_df(map_symbols=True).reset_index(drop=False)

def one(date,era,path):
    d=load(path); side=d.side.astype(str); size=pd.to_numeric(d['size'],errors='coerce').fillna(0.0); px=pd.to_numeric(d.price,errors='coerce'); bid=pd.to_numeric(d.bid_px_00,errors='coerce'); ask=pd.to_numeric(d.ask_px_00,errors='coerce')
    valid=px.notna()&bid.notna()&ask.notna()&(bid>0)&(ask>0)&(bid<ask)
    sell=valid&(px<=bid+EPS); buy=valid&(px>=ask-EPS); predA=sell&~buy; predB=buy&~sell
    known=valid&side.isin(['A','B']); cls=known&(predA|predB); correct=(side.eq('A')&predA)|(side.eq('B')&predB)
    n=side.isin(SIDE_NONE); nv=n&valid; ncls=nv&(predA|predB)
    total_vol=float(size.sum()); nvol=float(size[n].sum()); nvalidvol=float(size[nv].sum()); nclsvol=float(size[ncls].sum()); knownclsvol=float(size[cls].sum()); correctvol=float(size[cls&correct].sum())
    return {'era':era,'date':date,'records':int(len(d)),'total_volume':total_vol,'n_records':int(n.sum()),'n_record_rate':float(n.mean()),'n_volume':nvol,'n_volume_share':nvol/total_vol if total_vol else None,'n_valid_bbo_volume':nvalidvol,'n_touch_classifiable_volume':nclsvol,'n_touch_classifiable_volume_fraction_of_n_valid':nclsvol/nvalidvol if nvalidvol else None,'n_unresolved_volume':nvalidvol-nclsvol,'known_touch_classifiable_volume':knownclsvol,'known_touch_correct_volume':correctvol,'known_touch_volume_weighted_accuracy':correctvol/knownclsvol if knownclsvol else None}

def aggregate(g):
    tv=float(g.total_volume.sum()); nv=float(g.n_volume.sum()); nvv=float(g.n_valid_bbo_volume.sum()); ncv=float(g.n_touch_classifiable_volume.sum()); kv=float(g.known_touch_classifiable_volume.sum()); kc=float(g.known_touch_correct_volume.sum())
    return {'sessions':int(len(g)),'total_volume':tv,'n_volume':nv,'n_volume_share':nv/tv if tv else None,'n_touch_classifiable_volume_fraction_of_n_valid':ncv/nvv if nvv else None,'known_touch_volume_weighted_accuracy':kc/kv if kv else None}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw-root',required=True); ap.add_argument('--sessions',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); root=Path(a.raw_root); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    s=pd.read_csv(a.sessions); era=dict(zip(s.research_trading_date.astype(str),s.era.astype(str))); rows=[]
    for date,e in era.items():
        f=list(root.rglob(f'{date}__tbbo.dbn.zst'))
        if len(f)!=1: raise SystemExit(f'expected one TBBO {date}, got {len(f)}')
        rows.append(one(date,e,f[0]))
    d=pd.DataFrame(rows); d.to_csv(out/'n_volume_by_session.csv',index=False)
    byera=[]
    for e,g in d.groupby('era',sort=True): z=aggregate(g); z['era']=e; byera.append(z)
    result={'version':'COMEX_V4_PILOT12_N_VOLUME_V1','market_data_download_performed':False,'source':'existing paid TBBO pilot artifact','overall':aggregate(d),'by_era':byera,'max_session_n_volume_share':float(d.n_volume_share.max()),'max_session_n_volume_share_date':str(d.loc[d.n_volume_share.idxmax(),'date']),'note':'Native N is not assumed missing at random. Touch-rule recovery is evaluated by traded volume as well as record count.'}
    (out/'n_volume_summary.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
if __name__=='__main__':main()
