#!/usr/bin/env python3
# Triggered after explicit user authorization: GO CME 20 (2026-08-21).
import json, os
from pathlib import Path
import databento as db

out=Path('mnq-databento/results/cost_probe'); out.mkdir(parents=True, exist_ok=True)
client=db.Historical(os.environ['DATABENTO_API_KEY'])
base={
  'dataset':'GLBX.MDP3',
  'symbols':['NQ.v.0'],
  'schema':'ohlcv-1m',
  'stype_in':'continuous',
}
requests={
  'missing_tail_aug20': {**base, 'start':'2026-08-20T17:40:00Z', 'end':'2026-08-20T20:00:00Z'},
  'full_rth_aug20': {**base, 'start':'2026-08-20T13:30:00Z', 'end':'2026-08-20T20:00:00Z'},
}
result={'status':'DATABENTO_AUG20_COST_ESTIMATE_OK','requests':{},'data_downloaded':False,'secret_exposed':False}
try:
    for name, params in requests.items():
        result['requests'][name]={'request':params,'estimated_cost_usd':float(client.metadata.get_cost(**params))}
except Exception as e:
    result={'status':'DATABENTO_AUG20_COST_ESTIMATE_FAILED','error_type':type(e).__name__,'error':str(e),'data_downloaded':False,'secret_exposed':False}
(out/'RESULT.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
