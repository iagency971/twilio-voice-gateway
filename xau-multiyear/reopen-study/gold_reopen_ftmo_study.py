#!/usr/bin/env python3
import csv, io, json, math, os, statistics, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
CORE_ENTRY_MINUTES = [45,46,47,48,49]
DIAG_ENTRY_MINUTES = [50]
ALL_ENTRY_MINUTES = CORE_ENTRY_MINUTES + DIAG_ENTRY_MINUTES
POST_MINUTES = list(range(0,11))
ARCHIVE_BASE = 'https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd/{side}/m1/xauusd_{side}_m1_{y}_{m:02d}.csv'
SWAP_BASE_COSTS = [0.0,0.10,0.25,0.50,0.75,1.00,1.50,2.00,3.00]
EXTRA_SLIPPAGE_COSTS = [0.0,0.10,0.25,0.50,1.00,2.00]

def q(xs,p):
    xs=sorted(float(x) for x in xs)
    if not xs:return None
    if len(xs)==1:return xs[0]
    z=(len(xs)-1)*p; lo=int(math.floor(z)); hi=int(math.ceil(z))
    if lo==hi:return xs[lo]
    return xs[lo]*(hi-z)+xs[hi]*(z-lo)

def basic(xs):
    xs=[float(x) for x in xs]
    if not xs:return {'N':0}
    pos=[x for x in xs if x>0]; neg=[x for x in xs if x<0]
    gp=sum(pos); gl=-sum(neg)
    return {'N':len(xs),'mean':statistics.fmean(xs),'median':statistics.median(xs),
            'win_pct':100*len(pos)/len(xs),'flat_pct':100*sum(x==0 for x in xs)/len(xs),
            'p10':q(xs,.10),'p25':q(xs,.25),'p75':q(xs,.75),'p90':q(xs,.90),
            'avg_win':statistics.fmean(pos) if pos else None,
            'avg_loss':statistics.fmean(neg) if neg else None,
            'pf':gp/gl if gl>0 else None}

def dist(xs):
    xs=[float(x) for x in xs]
    if not xs:return {'N':0}
    return {'N':len(xs),'mean':statistics.fmean(xs),'median':statistics.median(xs),
            'p25':q(xs,.25),'p50':q(xs,.5),'p75':q(xs,.75),'p90':q(xs,.90),'p95':q(xs,.95)}

def wanted(d):
    return (d.hour==16 and 45<=d.minute<=50) or (d.hour==18 and 0<=d.minute<=10)

def load_archive_month(side,y,m):
    url=ARCHIVE_BASE.format(side=side,y=y,m=m)
    req=urllib.request.Request(url,headers={'User-Agent':'gold-reopen-ftmo-study'})
    out={}; mx=None
    with urllib.request.urlopen(req,timeout=120) as resp:
        for row in csv.DictReader(io.TextIOWrapper(resp,encoding='utf-8')):
            du=datetime.fromtimestamp(int(float(row['timestamp']))/1000,timezone.utc)
            if mx is None or du>mx:mx=du
            d=du.astimezone(NY)
            if wanted(d):
                out[f'{d.date().isoformat()}|{d.hour:02d}:{d.minute:02d}']={
                    'open':float(row['open']),'high':float(row['high']),
                    'low':float(row['low']),'close':float(row['close']),
                    'origin':'archive','utc':du.isoformat()}
    return side,y,m,out,mx.isoformat() if mx else None

def parse_tail(path,side,store,cutoff=None):
    if not path or not os.path.exists(path):return cutoff
    with open(path,newline='') as f:
        for row in csv.DictReader(f):
            raw=row.get('timestamp') or row.get('time') or row.get('date')
            if raw is None:continue
            try:
                x=float(raw); du=datetime.fromtimestamp(x/1000 if x>1e10 else x,timezone.utc)
            except Exception:
                du=datetime.fromisoformat(str(raw).replace('Z','+00:00'))
                if du.tzinfo is None:du=du.replace(tzinfo=timezone.utc)
                du=du.astimezone(timezone.utc)
            if cutoff is None or du>cutoff:cutoff=du
            d=du.astimezone(NY)
            if wanted(d):
                store[side][f'{d.date().isoformat()}|{d.hour:02d}:{d.minute:02d}']={
                    'open':float(row['open']),'high':float(row['high']),
                    'low':float(row['low']),'close':float(row['close']),
                    'origin':'tail','utc':du.isoformat()}
    return cutoff

def active(bs):
    if any(b is None for b in bs):return False
    vals=[]
    for b in bs:vals += [b['open'],b['high'],b['low'],b['close']]
    return max(vals)-min(vals)>1e-9

def event_type_and_prev(d):
    wd=d.weekday()
    if wd==6:return 'WEEKEND',d-timedelta(days=2)
    if wd in (0,1,2,3):return 'NORMAL',d
    return None,None

def swap_multiplier(prev_date,typ):
    if typ=='NORMAL':return 3 if prev_date.weekday()==2 else 1
    return 1

def build_events(store):
    def g(side,d,h,m):return store[side].get(f'{d.isoformat()}|{h:02d}:{m:02d}')
    candidates=[]
    for k in store['bid']:
        ds,ts=k.split('|')
        if ts=='18:00':candidates.append(datetime.fromisoformat(ds).date())
    events=[]; reject={'missing':0,'inactive':0,'negative_spread':0}
    for d in sorted(set(candidates)):
        typ,prev=event_type_and_prev(d)
        if typ is None:continue
        pre_bid=[g('bid',prev,16,m) for m in ALL_ENTRY_MINUTES]
        pre_ask=[g('ask',prev,16,m) for m in ALL_ENTRY_MINUTES]
        post_bid=[g('bid',d,18,m) for m in POST_MINUTES]
        if any(x is None for x in pre_bid+pre_ask+post_bid):reject['missing']+=1;continue
        if not active(pre_bid[:5]) or not active(post_bid):reject['inactive']+=1;continue
        spreads=[pre_ask[i]['open']-pre_bid[i]['open'] for i in range(len(ALL_ENTRY_MINUTES))]
        if any(s < -1e-9 for s in spreads):reject['negative_spread']+=1;continue
        e={'date':d.isoformat(),'year':d.year,'month':d.month,'type':typ,
           'entry_weekday':prev.strftime('%A'),'entry_weekday_num':prev.weekday(),
           'swap_mult':swap_multiplier(prev,typ),
           'bid_1800_open':post_bid[0]['open'],'bid_1805_open':post_bid[5]['open'],
           'bid_1800_close':post_bid[0]['close'],'bid_1804_close':post_bid[4]['close'],
           'missed_1800_to_1805_open':post_bid[5]['open']-post_bid[0]['open'],
           'missed_1800close_to_1805open':post_bid[5]['open']-post_bid[0]['close'],
           'entries':{}}
        for idx,m in enumerate(ALL_ENTRY_MINUTES):
            ask=pre_ask[idx]['open']; bid=pre_bid[idx]['open']
            exits={'18:05_OPEN':post_bid[5]['open']-ask}
            for pm in range(5,11):exits[f'18:{pm:02d}_CLOSE']=post_bid[pm]['close']-ask
            e['entries'][f'16:{m:02d}']={'entry_ask':ask,'entry_bid':bid,'spread':ask-bid,
                'to_1800_open':post_bid[0]['open']-ask,'to_1800_close':post_bid[0]['close']-ask,
                'to_1805_open':post_bid[5]['open']-ask,'exits':exits}
        events.append(e)
    return events,reject

def summary_for(es, entry='16:45'):
    out={'N':len(es),'entry':entry}
    if not es:return out
    out['spread']=dist([e['entries'][entry]['spread'] for e in es])
    out['to_1800_open']=basic([e['entries'][entry]['to_1800_open'] for e in es])
    out['to_1800_close']=basic([e['entries'][entry]['to_1800_close'] for e in es])
    out['to_1805_open']=basic([e['entries'][entry]['to_1805_open'] for e in es])
    out['missed_1800_to_1805_open']=basic([e['missed_1800_to_1805_open'] for e in es])
    out['missed_1800close_to_1805open']=basic([e['missed_1800close_to_1805open'] for e in es])
    exit_keys=list(es[0]['entries'][entry]['exits'].keys())
    out['exit']={k:basic([e['entries'][entry]['exits'][k] for e in es]) for k in exit_keys}
    out['swap_sensitivity_1805_open']={}
    for c in SWAP_BASE_COSTS:
        xs=[e['entries'][entry]['exits']['18:05_OPEN'] - c*e['swap_mult'] for e in es]
        out['swap_sensitivity_1805_open'][str(c)]=basic(xs)
    out['extra_slippage_sensitivity_1805_open']={}
    for c in EXTRA_SLIPPAGE_COSTS:
        xs=[e['entries'][entry]['exits']['18:05_OPEN'] - c for e in es]
        out['extra_slippage_sensitivity_1805_open'][str(c)]=basic(xs)
    avg_mult=statistics.fmean([e['swap_mult'] for e in es])
    gross_mean=out['exit']['18:05_OPEN']['mean']
    out['avg_swap_multiplier']=avg_mult
    out['break_even_base_swap_price_units_no_extra_slippage']=gross_mean/avg_mult if avg_mult else None
    out['break_even_total_flat_extra_cost_price_units']=gross_mean
    return out

def summarize_entries(es):
    out={'N':len(es),'entries':{}}
    for m in CORE_ENTRY_MINUTES:out['entries'][f'16:{m:02d}']=summary_for(es,f'16:{m:02d}')
    out['diagnostic_16:50']=summary_for(es,'16:50')
    return out

def main():
    tasks=[]
    for side in ('bid','ask'):
        for y in range(2020,2027):
            maxm=8 if y==2026 else 12
            for m in range(1,maxm+1):tasks.append((side,y,m))
    store={'bid':{},'ask':{}}; archive_max={'bid':None,'ask':None}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs=[ex.submit(load_archive_month,*t) for t in tasks]
        for fut in as_completed(futs):
            side,y,m,o,mx=fut.result();store[side].update(o)
            if mx and (archive_max[side] is None or mx>archive_max[side]):archive_max[side]=mx
    tail_max={'bid':parse_tail('tail_bid/recent_bid.csv','bid',store,None),
              'ask':parse_tail('tail_ask/recent_ask.csv','ask',store,None)}
    events,reject=build_events(store)
    out={'meta':{'timezone':'America/New_York','core_entries':['16:45','16:46','16:47','16:48','16:49'],
                 'diagnostic_entry':'16:50','first_ftmo_exit':'18:05_OPEN','archive_max':archive_max,
                 'tail_max':{k:(v.isoformat() if hasattr(v,'isoformat') else v) for k,v in tail_max.items()},
                 'reject':reject,'N_events':len(events)},'all_years':{},'by_year':{},
         '2026_by_month':{},'2026_by_weekday':{}}
    for typ in ('NORMAL','WEEKEND'):
        es=[e for e in events if e['type']==typ]; out['all_years'][typ]=summarize_entries(es)
    for y in range(2020,2027):
        out['by_year'][str(y)]={}
        for typ in ('NORMAL','WEEKEND'):
            es=[e for e in events if e['year']==y and e['type']==typ]
            out['by_year'][str(y)][typ]=summarize_entries(es)
    for m in range(1,9):
        es=[e for e in events if e['year']==2026 and e['month']==m and e['type']=='NORMAL']
        out['2026_by_month'][f'{m:02d}']=summarize_entries(es)
    for wd in range(4):
        es=[e for e in events if e['year']==2026 and e['type']=='NORMAL' and e['entry_weekday_num']==wd]
        out['2026_by_weekday'][str(wd)]=summarize_entries(es)
    print(json.dumps(out,sort_keys=True))

if __name__=='__main__':main()
