#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
import databento as db

BITS={2:'F_PUBLISHER_SPECIFIC',4:'F_MAYBE_BAD_BOOK',8:'F_BAD_TS_RECV',16:'F_MBP',32:'F_SNAPSHOT',64:'F_TOB',128:'F_LAST'}

def load(path):
    x=db.DBNStore.from_file(path).to_df(map_symbols=True).reset_index(drop=False)
    if 'ts_event' in x:x['ts_event']=pd.to_datetime(x['ts_event'],utc=True)
    return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-root',required=True);ap.add_argument('--sessions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);root=Path(a.raw_root);s=pd.read_csv(a.sessions);rows=[]
    for r in s.itertuples():
        fs=list(root.rglob(f'{r.research_trading_date}__trades.dbn.zst'))
        if len(fs)!=1:raise SystemExit(f'expected one trades file for {r.research_trading_date}, got {len(fs)}')
        x=load(fs[0]);flags=pd.to_numeric(x.get('flags',pd.Series(0,index=x.index)),errors='coerce').fillna(0).astype('int64');price=pd.to_numeric(x.get('price',pd.Series(dtype=float)),errors='coerce');size=pd.to_numeric(x.get('size',pd.Series(dtype=float)),errors='coerce');side=x.get('side',pd.Series(dtype=object)).astype(str);seq=pd.to_numeric(x.get('sequence',pd.Series(dtype=float)),errors='coerce')
        row={'research_trading_date':str(r.research_trading_date),'era':str(r.era),'records':int(len(x)),'price_grid_0_1_violation_records':int(((price*10-(price*10).round()).abs()>1e-6).fillna(True).sum()),'nonpositive_size_records':int((size<=0).fillna(True).sum()),'sequence_backward_steps':int((seq.diff()<0).sum()),'side_values':'|'.join(sorted(side.dropna().unique()))}
        for bit,name in BITS.items():row[name+'_records']=int(((flags & bit)!=0).sum())
        row['unknown_flag_bits_records']=int(((flags & ~sum(BITS.keys()))!=0).sum())
        rows.append(row)
    q=pd.DataFrame(rows);q.to_csv(out/'pilot_flags_qa_by_session.csv',index=False)
    totals={c:int(q[c].sum()) for c in q.columns if c.endswith('_records')}
    result={'version':'COMEX_PILOT_FLAGS_QA_V1','market_data_download_performed':False,'source':'existing paid 12-session trades artifact','sessions':int(len(q)),'records':int(q.records.sum()),'totals':totals,'side_values_union':sorted(set('|'.join(q.side_values).split('|'))),'blocking':{'price_grid_clean':bool(totals.get('price_grid_0_1_violation_records',0)==0),'sizes_positive':bool(totals.get('nonpositive_size_records',0)==0),'sequence_never_backward':bool(int(q.sequence_backward_steps.sum())==0),'no_unexpected_schema_flags':bool(sum(totals.get(f'{x}_records',0) for x in ['F_MBP','F_SNAPSHOT','F_TOB'])==0),'no_unknown_flag_bits':bool(totals.get('unknown_flag_bits_records',0)==0)},'note':'F_MAYBE_BAD_BOOK and F_BAD_TS_RECV are reported, not silently removed. Their handling follows the frozen feature specification.'}
    (out/'pilot_flags_qa.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
