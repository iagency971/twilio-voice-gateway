#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--entry',required=True);ap.add_argument('--confluence',required=True);ap.add_argument('--broad',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    e=pd.read_csv(a.entry);c=pd.read_csv(a.confluence);b=pd.read_csv(a.broad)
    model=(e.groupby(['family_stack','entry_model'],dropna=False).agg(eligible_events=('eligible_events','sum'),independent_sessions=('independent_sessions','sum'),years=('year','nunique')).reset_index().sort_values(['family_stack','entry_model']))
    model.to_csv(out/'dev_rank1_entry_model_summary.csv',index=False)
    sig=(e.groupby('signature',dropna=False).agg(eligible_events=('eligible_events','sum'),independent_sessions=('independent_sessions','sum'),years=('year','nunique')).reset_index().sort_values('eligible_events',ascending=False))
    sig.to_csv(out/'dev_rank1_signature_summary.csv',index=False)
    conf=(c.groupby('signature',dropna=False).agg(events=('events','sum'),independent_sessions=('independent_sessions','sum'),years=('year','nunique')).reset_index().sort_values('events',ascending=False))
    conf.to_csv(out/'dev_rank1_confluence_summary.csv',index=False)
    result={'version':'COMEX_DEV_RANK1_COVERAGE_SUMMARY_V1','market_data_download_performed':False,'broad_families':b.to_dict('records'),'family_entry_models':model.to_dict('records'),'all_signatures_entry_eligible':sig.to_dict('records'),'confluence_signatures':conf.to_dict('records'),'note':'Independent-session counts are summed across disjoint years. This is a feasibility inventory, not a power or validation claim.'}
    (out/'dev_rank1_coverage_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
