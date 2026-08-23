#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import pandas as pd
import run_v17_all24_branch_search as v17

_original_make=v17.make_fast_engine

def cached_make_fast_engine(BaseEngine,Trade,GLOBAL_MIN,GLOBAL_MAX):
    FE=_original_make(BaseEngine,Trade,GLOBAL_MIN,GLOBAL_MAX)
    class CachedFE(FE):
        _shared_maps={}
        def run(self,df,signals):
            key=(len(df),str(df.iloc[0]['datetime']),str(df.iloc[-1]['datetime']))
            if key not in self._shared_maps:
                self._shared_maps[key]={pd.Timestamp(x):i for i,x in enumerate(df['datetime'].tolist())}
            self._idxmap=self._shared_maps[key]
            return BaseEngine.run(self,df,signals)
    return CachedFE

v17.make_fast_engine=cached_make_fast_engine
import run_v18_selection_walkforward as v18
v18.OUT=Path('us100-zero-data/results/v18b_selection_walkforward_fast')

if __name__=='__main__':
    v18.main()
