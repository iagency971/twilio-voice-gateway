#!/usr/bin/env python3
import json, os
from pathlib import Path
import databento as db

out=Path('mnq-databento/results/cost_probe'); out.mkdir(parents=True, exist_ok=True)
key=os.environ['DATABENTO_API_KEY']
client=db.Historical(key)
params={
  'dataset':'GLBX.MDP3',
  'symbols':['NQ.v.0'],
  'schema':'ohlcv-1m',
  'stype_in':'continuous',
  'start':'2026-06-01T00:00:00Z',
  'end':'2026-08-21T00:00:00Z',
}
try:
    cost=float(client.metadata.get_cost(**params))
    result={'status':'DATABENTO_COST_ESTIMATE_OK','request':params,'estimated_cost_usd':cost,'data_downloaded':False,'secret_exposed':False}
except Exception as e:
    result={'status':'DATABENTO_COST_ESTIMATE_FAILED','request':params,'error_type':type(e).__name__,'error':str(e),'data_downloaded':False,'secret_exposed':False}
(out/'RESULT.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
