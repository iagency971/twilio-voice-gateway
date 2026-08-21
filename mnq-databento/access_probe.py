#!/usr/bin/env python3
import json, os
from pathlib import Path

present = bool(os.getenv('DATABENTO_API_KEY','').strip())
out = Path('mnq-databento/results/access_probe')
out.mkdir(parents=True, exist_ok=True)
result = {
    'status': 'DATABENTO_API_KEY_PRESENT' if present else 'DATABENTO_API_KEY_MISSING',
    'secret_value_exposed': False,
    'note': 'This probe records only whether the GitHub Actions secret exists; it never prints or persists the key.'
}
(out/'RESULT.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
