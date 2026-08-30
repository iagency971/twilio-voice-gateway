#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,tempfile,urllib.request
from pathlib import Path
import pandas as pd

REPO='kevingtlin/Market-Data-Lab'

def args():
 p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);p.add_argument('--manifest',required=True);return p.parse_args()
def git_blob(data):return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
def main():
 a=args();out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='xau-v2-upstream-'))
 try:
  subprocess.run(['git','clone','--depth','1','--filter=blob:none','--no-checkout',f'https://github.com/{REPO}.git',str(tmp)],check=True)
  head=subprocess.check_output(['git','-C',str(tmp),'rev-parse','HEAD'],text=True).strip()
  tree=subprocess.check_output(['git','-C',str(tmp),'ls-tree','-r','HEAD','xauusd/bid/m1'],text=True)
  blobs={line.split('\t',1)[1]:line.split()[2] for line in tree.splitlines() if '\t' in line}
  months=pd.period_range('2019-11','2026-07',freq='M');files={}
  for per in months:
   fn=f'xauusd_bid_m1_{per.year:04d}_{per.month:02d}.csv';rel=f'xauusd/bid/m1/{fn}'
   if rel not in blobs:raise RuntimeError(f'missing upstream {rel}')
   url=f'https://raw.githubusercontent.com/{REPO}/{head}/{rel}';data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'xau-e-zone-v2'}),timeout=180).read()
   got=git_blob(data)
   if got!=blobs[rel]:raise RuntimeError(f'{fn}: git blob mismatch {got} != {blobs[rel]}')
   p=out/fn;p.write_bytes(data);d=pd.read_csv(p)
   if list(d.columns)!=['timestamp','open','high','low','close']:raise RuntimeError(f'{fn}: schema {list(d.columns)}')
   t=pd.to_datetime(d.timestamp,unit='ms',utc=True)
   files[fn]={'repository_path':rel,'git_blob':got,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'rows':int(len(d)),'first_time_utc':t.min().isoformat() if len(t) else None,'last_time_utc':t.max().isoformat() if len(t) else None}
  m={'status':'E_ZONE_V2_COMMIT_PINNED_M1_ACQUISITION_PASS','repository':REPO,'upstream_commit':head,'months':len(files),'files':files}
  Path(a.manifest).write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':m['status'],'upstream_commit':head,'months':len(files)},indent=2))
 finally:shutil.rmtree(tmp,ignore_errors=True)
if __name__=='__main__':main()
