#!/usr/bin/env python3
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

SEED=20260829
BOOT_N=5000
MIN_VALID=4750

def smd(a,b):
 a=np.asarray(a,float);b=np.asarray(b,float);a=a[np.isfinite(a)];b=b[np.isfinite(b)]
 if not len(a) or not len(b):return None
 den=np.sqrt((np.var(a,ddof=0)+np.var(b,ddof=0))/2.0)
 if den<=0:return 0.0 if abs(np.mean(a)-np.mean(b))<1e-15 else float('inf')
 return float((np.mean(a)-np.mean(b))/den)

def session_bootstrap(d,metric,seed=SEED,n=BOOT_N,session_col='session_date_ny'):
 ss=np.array(sorted(d[session_col].astype(str).unique()));groups={s:d[d[session_col].astype(str)==s] for s in ss};rng=np.random.default_rng(seed);vals=[]
 for _ in range(n):
  picks=rng.choice(ss,size=len(ss),replace=True);x=pd.concat([groups[s] for s in picks],ignore_index=True);v=metric(x)
  if v is not None and np.isfinite(v):vals.append(float(v))
 ok=len(vals)>=MIN_VALID
 return {'requested':n,'valid':len(vals),'minimum_valid':MIN_VALID,'ci95':[float(np.quantile(vals,.025)),float(np.quantile(vals,.975))] if ok else [None,None]}

def auc(d,score='displayed_raw_score'):
 return None if not len(d) or d.primary_binary_label.nunique()!=2 else float(roc_auc_score(d.primary_binary_label.astype(int),d[score].astype(float)))

def q4q1(d):
 a=d[d.fixed_quartile=='Q1'];b=d[d.fixed_quartile=='Q4']
 return None if not len(a) or not len(b) else float(b.primary_binary_label.mean()-a.primary_binary_label.mean())

def holm_adjust(ps):
 valid=sorted([(k,float(v)) for k,v in ps.items() if v is not None],key=lambda x:x[1]);m=len(valid);out={k:None for k in ps};running=0.0
 for i,(k,p) in enumerate(valid):running=max(running,min(1.0,(m-i)*p));out[k]=running
 return out
