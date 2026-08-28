#!/usr/bin/env python3
import csv, io, json, math, os, statistics, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
ENTRY_MINUTES = list(range(55, 60))
EXIT_MINUTES = list(range(0, 5))  # 18:00 close = 1 minute held after reopen ... 18:04 close = 5 minutes
SL_GRID = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 20.0]
TP_GRID = [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 20.0]
ARCHIVE_BASE = 'https://raw.githubusercontent.com/kevingtlin/Market-Data-Lab/main/xauusd/{side}/m1/xauusd_{side}_m1_{y}_{m:02d}.csv'


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    z = (len(xs)-1) * p
    lo = int(math.floor(z)); hi = int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi-z) + xs[hi] * (z-lo)


def basic(xs):
    xs = [float(x) for x in xs]
    if not xs:
        return {'N': 0}
    pos = [x for x in xs if x > 0]
    neg = [x for x in xs if x < 0]
    s_pos = sum(pos); s_neg = -sum(neg)
    return {
        'N': len(xs),
        'win_pct': 100*len(pos)/len(xs),
        'flat_pct': 100*sum(x == 0 for x in xs)/len(xs),
        'mean': statistics.fmean(xs),
        'median': statistics.median(xs),
        'p10': q(xs, .10), 'p25': q(xs, .25), 'p75': q(xs, .75), 'p90': q(xs, .90),
        'avg_win': statistics.fmean(pos) if pos else None,
        'avg_loss': statistics.fmean(neg) if neg else None,
        'pf': (s_pos/s_neg) if s_neg > 0 else None,
    }


def dist(xs):
    xs = [float(x) for x in xs]
    if not xs:
        return {'N': 0}
    return {
        'N': len(xs), 'mean': statistics.fmean(xs), 'median': statistics.median(xs),
        'p25': q(xs,.25), 'p50': q(xs,.50), 'p75': q(xs,.75), 'p90': q(xs,.90), 'p95': q(xs,.95)
    }


def load_archive_month(side, y, m):
    url = ARCHIVE_BASE.format(side=side, y=y, m=m)
    req = urllib.request.Request(url, headers={'User-Agent':'gold-reopen-5m-study'})
    out = {}
    maxutc = None
    with urllib.request.urlopen(req, timeout=120) as resp:
        for row in csv.DictReader(io.TextIOWrapper(resp, encoding='utf-8')):
            du = datetime.fromtimestamp(int(float(row['timestamp']))/1000, timezone.utc)
            maxutc = du if maxutc is None or du > maxutc else maxutc
            d = du.astimezone(NY)
            # Only minutes needed for the study: 16:55-16:59 and 18:00-18:04 ET.
            if (d.hour == 16 and 55 <= d.minute <= 59) or (d.hour == 18 and 0 <= d.minute <= 4):
                out[f'{d.date().isoformat()}|{d.hour:02d}:{d.minute:02d}'] = {
                    'open':float(row['open']), 'high':float(row['high']),
                    'low':float(row['low']), 'close':float(row['close']),
                    'origin':'archive', 'utc':du.isoformat()
                }
    return side, y, m, out, maxutc.isoformat() if maxutc else None


def parse_tail(path, side, store, cutoff):
    if not path or not os.path.exists(path):
        return cutoff
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            raw = row.get('timestamp') or row.get('time') or row.get('date')
            if raw is None:
                continue
            try:
                x = float(raw)
                du = datetime.fromtimestamp(x/1000 if x > 1e10 else x, timezone.utc)
            except Exception:
                du = datetime.fromisoformat(str(raw).replace('Z','+00:00'))
                if du.tzinfo is None: du = du.replace(tzinfo=timezone.utc)
                du = du.astimezone(timezone.utc)
            cutoff = du if cutoff is None or du > cutoff else cutoff
            d = du.astimezone(NY)
            if (d.hour == 16 and 55 <= d.minute <= 59) or (d.hour == 18 and 0 <= d.minute <= 4):
                store[side][f'{d.date().isoformat()}|{d.hour:02d}:{d.minute:02d}'] = {
                    'open':float(row['open']), 'high':float(row['high']),
                    'low':float(row['low']), 'close':float(row['close']),
                    'origin':'tail', 'utc':du.isoformat()
                }
    return cutoff


def active(bs):
    if any(b is None for b in bs):
        return False
    vals=[]
    for b in bs:
        vals += [b['open'], b['high'], b['low'], b['close']]
    return (max(vals)-min(vals)) > 1e-9


def simulate_stop(entry_ask, full_pre, post, sl, horizon):
    stop = entry_ask - sl
    # Full exposure starts at the entry minute. BID open can already be below a very tight stop because entry is at ASK.
    for b in full_pre:
        if b['open'] <= stop:
            return b['open'] - entry_ask, 'PRE_OPEN'
        if b['low'] <= stop:
            return -sl, 'PRE_TOUCH'
    # Gap-aware: if market reopens below stop, fill at the first available BID, not the stale stop price.
    for j, b in enumerate(post[:horizon]):
        if b['open'] <= stop:
            return b['open'] - entry_ask, 'GAP_OPEN' if j == 0 else 'POST_OPEN'
        if b['low'] <= stop:
            return -sl, 'POST_TOUCH'
    return post[horizon-1]['close'] - entry_ask, 'TIME_EXIT'


def event_type_and_prev(d):
    wd = d.weekday()
    if wd == 6:  # Sunday reopening = Monday trading session
        return 'WEEKEND', d - timedelta(days=2)
    if wd in (0,1,2,3):
        return 'NORMAL', d
    return None, None


def build_events(store):
    def g(side, d, h, m):
        return store[side].get(f'{d.isoformat()}|{h:02d}:{m:02d}')
    candidates=[]
    for k in store['bid']:
        ds, ts = k.split('|')
        if ts == '18:00': candidates.append(datetime.fromisoformat(ds).date())
    events=[]; reject_missing=0; reject_inactive=0; reject_spread=0
    for d in sorted(set(candidates)):
        typ, prev = event_type_and_prev(d)
        if typ is None: continue
        pre_bid=[g('bid', prev, 16, m) for m in ENTRY_MINUTES]
        pre_ask=[g('ask', prev, 16, m) for m in ENTRY_MINUTES]
        post_bid=[g('bid', d, 18, m) for m in EXIT_MINUTES]
        if any(x is None for x in pre_bid+pre_ask+post_bid):
            reject_missing += 1; continue
        if not active(pre_bid) or not active(post_bid):
            reject_inactive += 1; continue
        spreads=[pre_ask[i]['open']-pre_bid[i]['open'] for i in range(5)]
        if any(s < -1e-9 for s in spreads):
            reject_spread += 1; continue
        e={'date':d.isoformat(),'year':d.year,'type':typ,'entries':{},
           'reopen_bid_open':post_bid[0]['open'],'reopen_bid_close_1m':post_bid[0]['close']}
        for idx, m in enumerate(ENTRY_MINUTES):
            entry_ask=pre_ask[idx]['open']; entry_bid=pre_bid[idx]['open']
            # From the actual entry minute onward, include remaining pre-close BID path.
            pre_path=pre_bid[idx:]
            full_path=pre_path+post_bid
            exits={}
            mfe_by_h={}; mae_by_h={}
            for h in range(1,6):
                exits[str(h)] = post_bid[h-1]['close'] - entry_ask
                path_h = pre_path + post_bid[:h]
                mfe_by_h[str(h)] = max(b['high'] for b in path_h) - entry_ask
                mae_by_h[str(h)] = entry_ask - min(b['low'] for b in path_h)
            pre_mfe=max(b['high'] for b in pre_path)-entry_ask
            pre_mae=entry_ask-min(b['low'] for b in pre_path)
            post_mfe5=max(b['high'] for b in post_bid)-entry_ask
            post_mae5=entry_ask-min(b['low'] for b in post_bid)
            total_mfe5=max(b['high'] for b in full_path)-entry_ask
            total_mae5=entry_ask-min(b['low'] for b in full_path)
            stops={}
            for sl in SL_GRID:
                stops[str(sl)]={}
                for h in (1,3,5):
                    pnl, why=simulate_stop(entry_ask, pre_path, post_bid, sl, h)
                    stops[str(sl)][str(h)]={'pnl':pnl,'reason':why}
            e['entries'][str(m)]={
                'entry_ask':entry_ask, 'entry_bid':entry_bid, 'spread':entry_ask-entry_bid,
                'gap_to_bid_open':post_bid[0]['open']-entry_ask,
                'exits':exits, 'mfe_by_h':mfe_by_h, 'mae_by_h':mae_by_h,
                'pre_mfe':pre_mfe, 'pre_mae':pre_mae,
                'post_mfe5':post_mfe5, 'post_mae5':post_mae5,
                'total_mfe5':total_mfe5, 'total_mae5':total_mae5,
                'stops':stops
            }
        events.append(e)
    return events, {'missing':reject_missing,'inactive':reject_inactive,'negative_spread':reject_spread}


def summarize(es):
    out={'N':len(es),'entry':{}}
    for m in ENTRY_MINUTES:
        key=str(m)
        ex={}
        for h in range(1,6):
            xs=[e['entries'][key]['exits'][str(h)] for e in es]
            ex[str(h)]=basic(xs)
        total_mfe=[max(0.0,e['entries'][key]['total_mfe5']) for e in es]
        total_mae=[max(0.0,e['entries'][key]['total_mae5']) for e in es]
        pre_mfe=[max(0.0,e['entries'][key]['pre_mfe']) for e in es]
        pre_mae=[max(0.0,e['entries'][key]['pre_mae']) for e in es]
        post_mfe=[max(0.0,e['entries'][key]['post_mfe5']) for e in es]
        post_mae=[max(0.0,e['entries'][key]['post_mae5']) for e in es]
        winners5=[e for e in es if e['entries'][key]['exits']['5']>0]
        winner_mae=[max(0.0,e['entries'][key]['total_mae5']) for e in winners5]
        spread=[e['entries'][key]['spread'] for e in es]
        tp_reach={str(tp):100*sum(e['entries'][key]['post_mfe5']>=tp for e in es)/len(es) if es else None for tp in TP_GRID}
        stop_summary={}
        for sl in SL_GRID:
            slk=str(sl); stop_summary[slk]={}
            for h in (1,3,5):
                vals=[e['entries'][key]['stops'][slk][str(h)]['pnl'] for e in es]
                reasons=[e['entries'][key]['stops'][slk][str(h)]['reason'] for e in es]
                stop_summary[slk][str(h)]={
                    **basic(vals),
                    'stop_pct':100*sum(r!='TIME_EXIT' for r in reasons)/len(reasons) if reasons else None,
                    'gap_stop_pct':100*sum(r=='GAP_OPEN' for r in reasons)/len(reasons) if reasons else None,
                }
        out['entry'][f'16:{m}']={
            'spread':dist(spread), 'exit':ex,
            'pre_mfe':dist(pre_mfe), 'pre_mae':dist(pre_mae),
            'post_mfe5':dist(post_mfe), 'post_mae5':dist(post_mae),
            'total_mfe5':dist(total_mfe), 'total_mae5':dist(total_mae),
            'winner5_total_mae':dist(winner_mae),
            'post_tp_reach_pct':tp_reach,
            'stop':stop_summary,
        }
    # Best fixed time exit by mean PnL for each entry; descriptive, not claimed as OOS optimization.
    best={}
    for m in ENTRY_MINUTES:
        k=f'16:{m}'
        candidates=[]
        for h in range(1,6):
            b=out['entry'][k]['exit'][str(h)]
            candidates.append((b.get('mean',-1e99),h,b))
        candidates.sort(reverse=True,key=lambda x:x[0])
        mean,h,b=candidates[0]
        best[k]={'exit_minute':h,'mean':mean,'win_pct':b.get('win_pct'),'median':b.get('median'),'pf':b.get('pf')}
    out['best_fixed_exit_by_mean']=best
    return out


def compact_key(s):
    # Keep the log JSON useful but bounded: include full 2025/2026 and all-years groups; yearly 2020-24 uses reduced fields.
    return s


def reduce_year(summary):
    out={'N':summary['N'],'best_fixed_exit_by_mean':summary['best_fixed_exit_by_mean'],'entry':{}}
    for k,v in summary['entry'].items():
        out['entry'][k]={
            'exit':v['exit'],
            'total_mfe5':v['total_mfe5'],'total_mae5':v['total_mae5'],
            'winner5_total_mae':v['winner5_total_mae'],
            'spread':v['spread']
        }
    return out


def main():
    tasks=[]
    for side in ('bid','ask'):
        for y in range(2020,2027):
            maxm=8 if y==2026 else 12
            for m in range(1,maxm+1): tasks.append((side,y,m))
    store={'bid':{},'ask':{}}; archive_max={'bid':None,'ask':None}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs=[ex.submit(load_archive_month,*t) for t in tasks]
        for fut in as_completed(futs):
            side,y,m,o,mx=fut.result();store[side].update(o)
            if mx and (archive_max[side] is None or mx>archive_max[side]):archive_max[side]=mx
    tail_max={'bid':None,'ask':None}
    tail_max['bid']=parse_tail('tail_bid/recent_bid.csv','bid',store,tail_max['bid'])
    tail_max['ask']=parse_tail('tail_ask/recent_ask.csv','ask',store,tail_max['ask'])
    events,reject=build_events(store)
    groups={
        'ALL':summarize(events),
        'NORMAL':summarize([e for e in events if e['type']=='NORMAL']),
        'WEEKEND':summarize([e for e in events if e['type']=='WEEKEND']),
    }
    yearly={}
    for y in range(2020,2027):
        ys=[e for e in events if e['year']==y]
        yr={
            'ALL':summarize(ys),
            'NORMAL':summarize([e for e in ys if e['type']=='NORMAL']),
            'WEEKEND':summarize([e for e in ys if e['type']=='WEEKEND']),
        }
        if y < 2025:
            yr={k:reduce_year(v) for k,v in yr.items()}
        yearly[str(y)]=yr
    sample_2026=[]
    for e in events:
        if e['year']==2026 and e['type']=='NORMAL':
            sample_2026.append({
                'date':e['date'],'reopen_bid_open':e['reopen_bid_open'],'reopen_bid_close_1m':e['reopen_bid_close_1m'],
                'entry_1655_ask':e['entries']['55']['entry_ask'],'pnl_1m_1655':e['entries']['55']['exits']['1'],
                'pnl_5m_1655':e['entries']['55']['exits']['5']
            })
    result={
        'source':'Dukascopy XAUUSD M1 BID/ASK; archived monthly files overridden by direct current tail when available',
        'timezone':'America/New_York',
        'definitions':{
            'entry':'BUY at ASK open 16:55..16:59 ET before maintenance break; Sunday reopening uses Friday entries',
            'exit':'sell at BID close 18:00..18:04 ET = fixed 1..5 minute exits after reopening',
            'mfe_mae':'includes remaining pre-close exposure from the entry minute through 16:59 plus post-reopen path through 18:04',
            'post_mfe_mae':'post-reopen-only path through 18:04, still measured versus original ASK entry',
            'stop':'full-hold stop; if first BID at reopening is below stop, fill is first available BID (gap slippage), otherwise touch fills at stop',
            'tp':'descriptive post-reopen MFE reach only; no TP/SL sequencing is asserted from M1 bars'
        },
        'archive_max_utc':archive_max,
        'tail_max_utc':{k:(v.isoformat() if v else None) for k,v in tail_max.items()},
        'events':len(events),'rejected':reject,
        'groups':groups,'yearly':yearly,
        'recent_2026_normal_samples':sample_2026[-12:]
    }
    with open('reopen5m_results.json','w') as f:json.dump(result,f,indent=2,sort_keys=True)
    # Print a compact executive subset for connector-friendly logs.
    executive={'source':result['source'],'archive_max_utc':result['archive_max_utc'],'tail_max_utc':result['tail_max_utc'],'events':result['events'],'rejected':result['rejected'],'groups':{},'yearly':{},'recent_2026_normal_samples':result['recent_2026_normal_samples']}
    for g in ('NORMAL','WEEKEND'):
        s=groups[g]
        executive['groups'][g]={'N':s['N'],'best':s['best_fixed_exit_by_mean'],'entry':{}}
        for k,v in s['entry'].items():
            executive['groups'][g]['entry'][k]={
                'exit':v['exit'],'total_mfe5':v['total_mfe5'],'total_mae5':v['total_mae5'],
                'winner5_total_mae':v['winner5_total_mae'],'post_tp_reach_pct':v['post_tp_reach_pct'],
                'spread':v['spread'],
                'stop_1_2_3_5_10':{sl:v['stop'][sl] for sl in ('1.0','2.0','3.0','5.0','10.0')}
            }
    for y in range(2020,2027):
        executive['yearly'][str(y)]={}
        for g in ('NORMAL','WEEKEND'):
            s=yearly[str(y)][g]
            executive['yearly'][str(y)][g]={'N':s['N'],'best':s['best_fixed_exit_by_mean']}
            # exit table only, enough to compare regime by year
            executive['yearly'][str(y)][g]['exit']={k:v['exit'] for k,v in s['entry'].items()}
    print('EXECUTIVE_JSON_START')
    print(json.dumps(executive,sort_keys=True))
    print('EXECUTIVE_JSON_END')

if __name__=='__main__':
    main()
