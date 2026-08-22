#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

OUT = Path('ftmo-zero-data/results/ustec_v1')
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://raw.githubusercontent.com/CodyOutcast/Academic-Paper-Data-Source/main/OHLC-USTEC-M1-{}.csv'
DEV_YEARS = [2021, 2022, 2023]
VAL_YEAR = 2024
OPEN_MINUTE = 16 * 60 + 30
SIGNAL_CUTOFF_MINUTE = 19 * 60 + 30
FORCE_EXIT_MINUTE = 22 * 60 + 55

@dataclass(frozen=True)
class Candidate:
    family: str
    orb_min: int
    rr: float
    buffer_frac: float
    fail_bars: int = 5

    @property
    def name(self) -> str:
        return f'{self.family}_OR{self.orb_min}_RR{self.rr:.1f}_BUF{int(self.buffer_frac*100):02d}'

def candidates() -> list[Candidate]:
    out = []
    for fam in ('CONT', 'FAIL'):
        for orb in (15, 30):
            for rr in (1.0, 1.5):
                for buf in (0.0, 0.05):
                    out.append(Candidate(fam, orb, rr, buf))
    return out

def load_year(year: int) -> pd.DataFrame:
    if year >= 2025:
        raise RuntimeError('V1 outcome-blind guard: 2025+ access forbidden')
    df = pd.read_csv(BASE.format(year), sep=';')
    df.columns = [str(c).strip().lower() for c in df.columns]
    need = {'time','open','high','low','close','spread'}
    miss = need - set(df.columns)
    if miss:
        raise RuntimeError(f'{year}: missing columns {sorted(miss)}')
    df['time'] = pd.to_datetime(df['time'], format='%Y.%m.%d %H:%M:%S', errors='coerce')
    for c in ('open','high','low','close','volume','spread'):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['time','open','high','low','close','spread']).copy()
    df = df.sort_values('time').drop_duplicates('time', keep='last').reset_index(drop=True)
    df['date'] = df['time'].dt.date
    df['minute'] = df['time'].dt.hour * 60 + df['time'].dt.minute
    return df

def scenario_spread(s: float, stress: bool) -> float:
    s = float(max(s, 0.0))
    return max(s * 1.5, s + 1.0) if stress else s

def day_trade(day: pd.DataFrame, c: Candidate, stress: bool=False) -> Optional[dict]:
    day = day.sort_values('time').reset_index(drop=True)
    end_min = OPEN_MINUTE + c.orb_min - 1
    orb = day[(day.minute >= OPEN_MINUTE) & (day.minute <= end_min)]
    if len(orb) < c.orb_min - 1:
        return None
    or_high = float(orb.high.max())
    or_low = float(orb.low.min())
    width = or_high - or_low
    if not np.isfinite(width) or width <= 0:
        return None
    buffer = c.buffer_frac * width
    after = day[(day.minute > end_min) & (day.minute <= SIGNAL_CUTOFF_MINUTE)]
    if after.empty:
        return None

    signal_idx = None
    direction = None
    excursion_hi = None
    excursion_lo = None

    if c.family == 'CONT':
        for idx in after.index:
            r = day.loc[idx]
            if r.close > or_high + buffer:
                signal_idx, direction = idx, 'long'
                break
            if r.close < or_low - buffer:
                signal_idx, direction = idx, 'short'
                break
    else:
        break_idx = None
        break_side = None
        for idx in after.index:
            r = day.loc[idx]
            if r.close > or_high + buffer:
                break_idx, break_side = idx, 'up'
                break
            if r.close < or_low - buffer:
                break_idx, break_side = idx, 'down'
                break
        if break_idx is None:
            return None
        last = min(break_idx + c.fail_bars, len(day)-2)
        for idx in range(break_idx + 1, last + 1):
            r = day.loc[idx]
            if break_side == 'up' and r.close < or_high:
                signal_idx, direction = idx, 'short'
                seen = day.loc[break_idx:idx]
                excursion_hi = float(seen.high.max())
                excursion_lo = float(seen.low.min())
                break
            if break_side == 'down' and r.close > or_low:
                signal_idx, direction = idx, 'long'
                seen = day.loc[break_idx:idx]
                excursion_hi = float(seen.high.max())
                excursion_lo = float(seen.low.min())
                break

    if signal_idx is None or signal_idx + 1 >= len(day):
        return None
    ent_i = signal_idx + 1
    ebar = day.loc[ent_i]
    if int(ebar.minute) > SIGNAL_CUTOFF_MINUTE + 1:
        return None
    entry_spread = scenario_spread(ebar.spread, stress)
    slip_side = 0.5 if stress else 0.0
    entry_bid = float(ebar.open)

    if direction == 'long':
        entry = entry_bid + entry_spread + slip_side
        stop_bid = or_low if c.family == 'CONT' else float(excursion_lo)
        risk = entry - stop_bid
        if risk <= 0:
            return None
        target_bid = entry + c.rr * risk
    else:
        entry = entry_bid - slip_side
        stop_bid_struct = or_high if c.family == 'CONT' else float(excursion_hi)
        stop_ask = stop_bid_struct + entry_spread + slip_side
        risk = stop_ask - entry
        if risk <= 0:
            return None
        target_ask = entry - c.rr * risk

    exit_time = None
    exit_reason = None
    exit_price = None
    for i in range(ent_i, len(day)):
        b = day.loc[i]
        if int(b.minute) > FORCE_EXIT_MINUTE:
            break
        sp = scenario_spread(b.spread, stress)
        if direction == 'long':
            hit_stop = float(b.low) <= stop_bid
            hit_target = float(b.high) >= target_bid
            if hit_stop and hit_target:
                hit_target = False
            if hit_stop:
                exit_price = stop_bid - slip_side
                exit_reason = 'stop'; exit_time = b.time; break
            if hit_target:
                exit_price = target_bid - slip_side
                exit_reason = 'target'; exit_time = b.time; break
        else:
            ask_high = float(b.high) + sp
            ask_low = float(b.low) + sp
            hit_stop = ask_high >= stop_ask
            hit_target = ask_low <= target_ask
            if hit_stop and hit_target:
                hit_target = False
            if hit_stop:
                exit_price = stop_ask + slip_side
                exit_reason = 'stop'; exit_time = b.time; break
            if hit_target:
                exit_price = target_ask + slip_side
                exit_reason = 'target'; exit_time = b.time; break

    if exit_price is None:
        eligible = day[(day.index >= ent_i) & (day.minute <= FORCE_EXIT_MINUTE)]
        if eligible.empty:
            return None
        b = eligible.iloc[-1]
        sp = scenario_spread(b.spread, stress)
        if direction == 'long':
            exit_price = float(b.close) - slip_side
        else:
            exit_price = float(b.close) + sp + slip_side
        exit_reason = 'time'; exit_time = b.time

    pnl = (exit_price - entry) if direction == 'long' else (entry - exit_price)
    return {
        'date': str(ebar.date), 'entry_time': str(ebar.time), 'exit_time': str(exit_time),
        'direction': direction, 'family': c.family, 'candidate': c.name,
        'orb_min': c.orb_min, 'rr_cfg': c.rr, 'buffer_frac': c.buffer_frac,
        'or_high': or_high, 'or_low': or_low, 'or_width': width,
        'entry': entry, 'risk_points': risk, 'exit': exit_price,
        'exit_reason': exit_reason, 'r': float(pnl / risk),
        'entry_spread': float(entry_spread), 'stress': bool(stress),
    }

def run_candidate(df: pd.DataFrame, c: Candidate, stress=False) -> pd.DataFrame:
    rows = []
    for _, day in df.groupby('date', sort=True):
        t = day_trade(day, c, stress=stress)
        if t is not None:
            rows.append(t)
    return pd.DataFrame(rows)

def pf(a: np.ndarray):
    pos = a[a > 0].sum(); neg = -a[a < 0].sum()
    return float(pos/neg) if neg > 0 else (1e9 if pos > 0 else None)

def stat_frame(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {'n':0,'mean':None,'sum':0.0,'pf':None,'win_rate':None,'max_dd':None}
    a = tr.r.to_numpy(float); eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks-eq, 0.0)
    return {'n':int(len(a)),'mean':float(a.mean()),'sum':float(a.sum()),'pf':pf(a),
            'win_rate':float((a>0).mean()),'max_dd':float(dd.max(initial=0.0))}

def remove_best_mean(tr: pd.DataFrame, pct=0.10):
    if tr.empty: return None
    a=np.sort(tr.r.to_numpy(float)); n=max(1,int(math.ceil(len(a)*pct)))
    keep=a[:-n] if n < len(a) else np.array([])
    return float(keep.mean()) if len(keep) else None

def yearly(tr: pd.DataFrame) -> dict:
    if tr.empty: return {}
    z=tr.copy(); z['year']=pd.to_datetime(z.date).dt.year
    return {str(y):stat_frame(g) for y,g in z.groupby('year')}

def monthly_positive_rate(tr: pd.DataFrame):
    if tr.empty: return 0.0,0
    z=tr.copy(); z['month']=pd.to_datetime(z.date).dt.to_period('M').astype(str)
    s=z.groupby('month').r.sum()
    return float((s>0).mean()),int(len(s))

def half_sums(tr: pd.DataFrame):
    if tr.empty: return {'H1':0.0,'H2':0.0}
    d=pd.to_datetime(tr.date)
    return {'H1':float(tr.loc[d.dt.month<=6,'r'].sum()),'H2':float(tr.loc[d.dt.month>=7,'r'].sum())}

def dev_eligible(primary: pd.DataFrame, stress: pd.DataFrame):
    s=stat_frame(primary); ss=stat_frame(stress); ys=yearly(primary)
    pos_years=sum(1 for v in ys.values() if v['sum']>0)
    means=[v['mean'] for v in ys.values() if v['mean'] is not None]
    worst=min(means) if means else None; rb=remove_best_mean(primary,0.10)
    gates={'n_ge_180':s['n']>=180,'mean_ge_0_05':s['mean'] is not None and s['mean']>=0.05,
           'pf_ge_1_15':s['pf'] is not None and s['pf']>=1.15,
           'maxdd_le_15':s['max_dd'] is not None and s['max_dd']<=15,
           'positive_years_ge_2':pos_years>=2,
           'worst_year_mean_ge_m0_05':worst is not None and worst>=-0.05,
           'remove_best10_mean_ge_0':rb is not None and rb>=0,
           'stress_mean_gt_0':ss['mean'] is not None and ss['mean']>0,
           'stress_pf_ge_1_05':ss['pf'] is not None and ss['pf']>=1.05}
    detail={'primary':s,'stress':ss,'yearly':ys,'positive_years':pos_years,
            'worst_year_mean':worst,'remove_best10_mean':rb,'gates':gates}
    return all(gates.values()),detail

def score_dev(details: dict) -> float:
    p=details['primary']; worst=details['worst_year_mean'] if details['worst_year_mean'] is not None else -99
    return float(2.0*worst + p['mean'] + 0.02*math.log(max(p['n'],1)) - 0.01*p['max_dd'])

def validation_gate(primary: pd.DataFrame, stress: pd.DataFrame):
    s=stat_frame(primary); ss=stat_frame(stress); rb=remove_best_mean(primary,0.10)
    halves=half_sums(primary); mrate,nm=monthly_positive_rate(primary)
    gates={'n_ge_50':s['n']>=50,'mean_ge_0_05':s['mean'] is not None and s['mean']>=0.05,
           'pf_ge_1_15':s['pf'] is not None and s['pf']>=1.15,
           'maxdd_le_10':s['max_dd'] is not None and s['max_dd']<=10,
           'remove_best10_mean_ge_0':rb is not None and rb>=0,
           'stress_mean_gt_0':ss['mean'] is not None and ss['mean']>0,
           'stress_pf_ge_1_05':ss['pf'] is not None and ss['pf']>=1.05,
           'h1_positive':halves['H1']>0,'h2_positive':halves['H2']>0,
           'positive_month_rate_ge_55pct':mrate>=0.55}
    return all(gates.values()),{'primary':s,'stress':ss,'remove_best10_mean':rb,
                                'half_sums':halves,'positive_month_rate':mrate,
                                'active_months':nm,'gates':gates}

def qa(df: pd.DataFrame, year:int)->dict:
    return {'year':year,'rows':int(len(df)),'first':str(df.time.min()),'last':str(df.time.max()),
            'duplicates':int(df.duplicated('time').sum()),
            'bad_ohlc':int(((df.low>df.high)|(df.open<df.low)|(df.open>df.high)|(df.close<df.low)|(df.close>df.high)).sum()),
            'spread_mean':float(df.spread.mean()),'spread_median':float(df.spread.median()),
            'spread_p95':float(df.spread.quantile(.95)),
            'open_anchor_days':int(df[df.minute==OPEN_MINUTE].date.nunique())}

def main():
    frames={y:load_year(y) for y in DEV_YEARS+[VAL_YEAR]}
    qas={str(y):qa(frames[y],y) for y in frames}
    dev=pd.concat([frames[y] for y in DEV_YEARS],ignore_index=True).sort_values('time')
    val=frames[VAL_YEAR]
    dev_results={}; selected={}
    for c in candidates():
        p=run_candidate(dev,c,False); s=run_candidate(dev,c,True)
        ok,detail=dev_eligible(p,s)
        detail['candidate']=asdict(c); detail['name']=c.name; detail['eligible']=ok
        detail['robustness_score']=score_dev(detail) if ok else None
        dev_results[c.name]=detail
    for fam in ('CONT','FAIL'):
        eligible=[v for v in dev_results.values() if v['candidate']['family']==fam and v['eligible']]
        selected[fam]=max(eligible,key=lambda x:x['robustness_score'])['name'] if eligible else None
    validation={}; all_trades=[]; cand_by_name={c.name:c for c in candidates()}
    for fam,name in selected.items():
        if name is None:
            validation[fam]={'status':'DEV_FAMILY_REJECTED_NO_VALIDATION','selected':None}; continue
        c=cand_by_name[name]; p=run_candidate(val,c,False); s=run_candidate(val,c,True)
        ok,detail=validation_gate(p,s); detail['selected']=name
        detail['status']='VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS' if ok else 'VALIDATION_NO_GO'
        validation[fam]=detail
        if not p.empty:
            z=p.copy(); z['stage']='VALIDATION_2024_PRIMARY'; all_trades.append(z)
        if not s.empty:
            z=s.copy(); z['stage']='VALIDATION_2024_STRESS'; all_trades.append(z)
    result={'status':'USTEC_V1_DEV_VALIDATION_COMPLETE_2025_UNOPENED',
            'hard_constraint':'ZERO_PAID_EXTERNAL_DATA_REQUIRED_LIVE',
            'data_source':'Public GitHub CSV; repository identifies OHLC source as IC Markets USTEC M1',
            'partitions':{'DEV':'2021-2023','VALIDATION':'2024','OOS_2025':'SEALED_NOT_DOWNLOADED'},
            'data_qa':qas,'candidate_count':len(candidates()),'dev_results':dev_results,
            'selected_by_family':selected,'validation':validation,'oos_2025_opened':False,
            'notes':['No 2025 URL is requested anywhere in this V1 script.',
                     'A 2024 pass is only proxy evidence; FTMO-native Free Trial/demo validation remains mandatory.',
                     'No paid market-data subscription is required by either candidate family.']}
    (OUT/'RESULT.json').write_text(json.dumps(result,indent=2,allow_nan=False,default=str))
    rows=[]
    for v in dev_results.values():
        rows.append({'name':v['name'],'family':v['candidate']['family'],'eligible':v['eligible'],
                     'n':v['primary']['n'],'mean':v['primary']['mean'],'pf':v['primary']['pf'],
                     'max_dd':v['primary']['max_dd'],'stress_mean':v['stress']['mean'],
                     'stress_pf':v['stress']['pf'],'remove_best10_mean':v['remove_best10_mean'],
                     'worst_year_mean':v['worst_year_mean'],'score':v['robustness_score']})
    pd.DataFrame(rows).to_csv(OUT/'DEV_SCREEN.csv',index=False)
    if all_trades:
        pd.concat(all_trades,ignore_index=True).to_csv(OUT/'VALIDATION_TRADES.csv',index=False)
    print(json.dumps({'status':result['status'],'selected':selected,'validation':validation},indent=2,default=str))

if __name__=='__main__':
    main()
