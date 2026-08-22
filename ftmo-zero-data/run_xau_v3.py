#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path('ftmo-zero-data/results/xau_v3')
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://raw.githubusercontent.com/tiumbj/M1_XAUUSD/main/DAT_MT_XAUUSD_M1_{}.csv'
DEV_YEARS = [2021, 2022, 2023]
VAL_YEAR = 2024
ALL_YEARS = DEV_YEARS + [VAL_YEAR]
NY = 'America/New_York'
FIXED_EST = 'Etc/GMT+5'  # UTC-5; HistData timestamps do not apply DST.
SIGNAL_START = 8 * 60 + 20
SIGNAL_END = 12 * 60
FORCE_EXIT = 15 * 60 + 55
MAX_TRADES_DAY = 3
COOLDOWN_MIN = 30
COMMISSION_RATE = 0.000007  # 0.0007% of notional per side; price-equivalent for 100 oz = price*rate.
BOOT_SEED = 260822


@dataclass(frozen=True)
class Candidate:
    family: str
    rr: float
    stop_atr: float | None = None
    penetration_atr: float | None = None

    @property
    def name(self) -> str:
        if self.family.startswith('PB'):
            return f'{self.family}_SL{self.stop_atr:.1f}_RR{self.rr:.1f}'
        return f'{self.family}_PEN{int(self.penetration_atr * 100):02d}_RR{self.rr:.1f}'


def candidates() -> list[Candidate]:
    out: list[Candidate] = []
    for fam in ('PB_LONG', 'PB_BI'):
        for sl in (1.5, 2.0):
            for rr in (1.5, 2.0):
                out.append(Candidate(fam, rr=rr, stop_atr=sl))
    for fam in ('SWEEP_LONG', 'SWEEP_BI'):
        for pen in (0.0, 0.10):
            for rr in (1.5, 2.0):
                out.append(Candidate(fam, rr=rr, penetration_atr=pen))
    return out


def load_year(year: int) -> pd.DataFrame:
    if year >= 2025:
        raise RuntimeError('V3 outcome-blind guard: 2025+ access forbidden')
    names = ['date_s', 'time_s', 'open', 'high', 'low', 'close', 'volume']
    d = pd.read_csv(BASE.format(year), names=names, header=None)
    naive = pd.to_datetime(d.date_s.astype(str) + ' ' + d.time_s.astype(str),
                           format='%Y.%m.%d %H:%M', errors='coerce')
    fixed = pd.DatetimeIndex(naive).tz_localize(FIXED_EST)
    d['time'] = fixed.tz_convert(NY)
    for c in ('open', 'high', 'low', 'close', 'volume'):
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['time', 'open', 'high', 'low', 'close'])
    d = d.sort_values('time').drop_duplicates('time', keep='last')
    return d[['time', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    z = raw.set_index('time').sort_index()
    m5 = z.resample('5min', label='left', closed='left').agg(
        open=('open', 'first'), high=('high', 'max'), low=('low', 'min'),
        close=('close', 'last'), volume=('volume', 'sum'), count=('close', 'count'))
    m5 = m5.dropna(subset=['open', 'high', 'low', 'close'])
    m5 = m5[m5['count'] >= 4].copy()
    prev_close = m5.close.shift(1)
    tr = pd.concat([(m5.high - m5.low), (m5.high - prev_close).abs(),
                    (m5.low - prev_close).abs()], axis=1).max(axis=1)
    m5['atr14'] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    m5['ema20'] = m5.close.ewm(span=20, adjust=False).mean()
    m5['prev_close'] = m5.close.shift(1)
    m5['prev_ema20'] = m5.ema20.shift(1)

    h1 = z.resample('1h', label='right', closed='left').agg(
        close=('close', 'last'), count=('close', 'count'))
    h1 = h1.dropna(subset=['close'])
    h1 = h1[h1['count'] >= 45].copy()
    h1['h1_ema20'] = h1.close.ewm(span=20, adjust=False).mean()
    h1['h1_ema50'] = h1.close.ewm(span=50, adjust=False).mean()
    h1['h1_ema50_lag3'] = h1.h1_ema50.shift(3)
    h1 = h1.reset_index()[['time', 'h1_ema20', 'h1_ema50', 'h1_ema50_lag3']]

    m5 = m5.reset_index().sort_values('time')
    m5 = pd.merge_asof(m5, h1.sort_values('time'), on='time', direction='backward')
    m5['ny_date'] = m5.time.dt.date
    m5['minute'] = m5.time.dt.hour * 60 + m5.time.dt.minute

    # 17:00 NY session key; current morning belongs to the session that began the prior calendar date.
    m5['session_key'] = (m5.time - pd.Timedelta(hours=17)).dt.date
    sess = m5.groupby('session_key', sort=True).agg(sess_high=('high', 'max'), sess_low=('low', 'min'))
    sess['prev_session_high'] = sess.sess_high.shift(1)
    sess['prev_session_low'] = sess.sess_low.shift(1)
    high_map = sess.prev_session_high.to_dict()
    low_map = sess.prev_session_low.to_dict()
    m5['prev_session_high'] = m5.session_key.map(high_map)
    m5['prev_session_low'] = m5.session_key.map(low_map)

    return m5.dropna(subset=['atr14', 'ema20', 'prev_close', 'prev_ema20',
                             'h1_ema20', 'h1_ema50', 'h1_ema50_lag3']).reset_index(drop=True)


def scenario(stress: bool) -> tuple[float, float]:
    return (0.50, 0.05) if stress else (0.30, 0.0)


def comm_eq(price: float) -> float:
    return max(float(price), 0.0) * COMMISSION_RATE


def long_entry_net(bid_open: float, spread: float, slip: float) -> float:
    raw = bid_open + spread + slip
    return raw + comm_eq(raw)


def short_entry_net(bid_open: float, slip: float) -> float:
    raw = bid_open - slip
    return raw - comm_eq(raw)


def long_exit_net(bid: float, slip: float) -> float:
    raw = bid - slip
    return raw - comm_eq(raw)


def short_exit_net_from_bid(bid: float, spread: float, slip: float) -> float:
    ask = bid + spread + slip
    return ask + comm_eq(ask)


def pullback_signal(r: pd.Series, family: str) -> str | None:
    long_ok = (r.h1_ema20 > r.h1_ema50 and r.h1_ema50 > r.h1_ema50_lag3 and
               r.prev_close <= r.prev_ema20 and r.close > r.ema20)
    if long_ok:
        return 'long'
    if family == 'PB_BI':
        short_ok = (r.h1_ema20 < r.h1_ema50 and r.h1_ema50 < r.h1_ema50_lag3 and
                    r.prev_close >= r.prev_ema20 and r.close < r.ema20)
        if short_ok:
            return 'short'
    return None


def sweep_signal(r: pd.Series, c: Candidate, used_sides: set[str]) -> str | None:
    if not np.isfinite(r.prev_session_low) or not np.isfinite(r.prev_session_high):
        return None
    pen = float(c.penetration_atr) * float(r.atr14)
    if 'long' not in used_sides:
        if r.low <= r.prev_session_low - pen and r.close > r.prev_session_low:
            return 'long'
    if c.family == 'SWEEP_BI' and 'short' not in used_sides:
        if r.high >= r.prev_session_high + pen and r.close < r.prev_session_high:
            return 'short'
    return None


def simulate_trade(day: pd.DataFrame, signal_i: int, c: Candidate, side: str,
                   stress: bool) -> tuple[dict | None, int]:
    if signal_i + 1 >= len(day):
        return None, signal_i + 1
    sig = day.loc[signal_i]
    ent_i = signal_i + 1
    e = day.loc[ent_i]
    if int(e.minute) > SIGNAL_END + 5:
        return None, signal_i + 1

    spread, slip = scenario(stress)
    bid_open = float(e.open)
    atr = float(sig.atr14)
    if atr <= 0 or not np.isfinite(atr):
        return None, signal_i + 1

    if c.family.startswith('PB'):
        if side == 'long':
            stop_bid = bid_open - float(c.stop_atr) * atr
        else:
            stop_bid = bid_open + float(c.stop_atr) * atr
    else:
        if side == 'long':
            stop_bid = float(sig.low) - 0.10 * atr
        else:
            stop_bid = float(sig.high) + 0.10 * atr

    if side == 'long':
        if bid_open <= stop_bid:
            return None, signal_i + 1
        entry = long_entry_net(bid_open, spread, slip)
        stop_net = long_exit_net(stop_bid, slip)
        risk = entry - stop_net
        if risk <= 0:
            return None, signal_i + 1
        desired_target_net = entry + c.rr * risk
        # target Bid such that net sale proceeds equal desired_target_net.
        target_bid = (desired_target_net + slip) / (1.0 - COMMISSION_RATE)
        stop_trigger_bid = stop_bid
        target_trigger_bid = target_bid
    else:
        if bid_open >= stop_bid:
            return None, signal_i + 1
        entry = short_entry_net(bid_open, slip)
        stop_net = short_exit_net_from_bid(stop_bid, spread, slip)
        risk = stop_net - entry
        if risk <= 0:
            return None, signal_i + 1
        desired_target_net = entry - c.rr * risk
        # Ask at target is target_bid + spread. Solve net buy cost = desired_target_net.
        target_ask = (desired_target_net - slip) / (1.0 + COMMISSION_RATE)
        target_bid = target_ask - spread
        stop_trigger_bid = stop_bid
        target_trigger_bid = target_bid

    exit_i = None
    exit_net = None
    reason = None
    for j in range(ent_i, len(day)):
        b = day.loc[j]
        if int(b.minute) > FORCE_EXIT:
            break
        if side == 'long':
            hit_stop = float(b.low) <= stop_trigger_bid
            hit_target = float(b.high) >= target_trigger_bid
            if hit_stop and hit_target:
                hit_target = False
            if hit_stop:
                exit_i, exit_net, reason = j, long_exit_net(stop_bid, slip), 'stop'
                break
            if hit_target:
                exit_i, exit_net, reason = j, long_exit_net(target_bid, slip), 'target'
                break
        else:
            # Short SL/TP are Ask-triggered; fixed scenario spread lets us convert to Bid thresholds.
            ask_high = float(b.high) + spread
            ask_low = float(b.low) + spread
            stop_ask = stop_bid + spread
            target_ask = target_bid + spread
            hit_stop = ask_high >= stop_ask
            hit_target = ask_low <= target_ask
            if hit_stop and hit_target:
                hit_target = False
            if hit_stop:
                exit_i, exit_net, reason = j, short_exit_net_from_bid(stop_bid, spread, slip), 'stop'
                break
            if hit_target:
                exit_i, exit_net, reason = j, short_exit_net_from_bid(target_bid, spread, slip), 'target'
                break

    if exit_i is None:
        eligible = day[(day.index >= ent_i) & (day.minute <= FORCE_EXIT)]
        if eligible.empty:
            return None, signal_i + 1
        b = eligible.iloc[-1]
        exit_i = int(b.name)
        exit_net = long_exit_net(float(b.close), slip) if side == 'long' else short_exit_net_from_bid(float(b.close), spread, slip)
        reason = 'time'

    pnl = (exit_net - entry) if side == 'long' else (entry - exit_net)
    trade = {
        'date': str(e.ny_date), 'entry_time': str(e.time), 'exit_time': str(day.loc[exit_i].time),
        'family': c.family, 'candidate': c.name, 'direction': side,
        'entry_bid': bid_open, 'entry_net': entry, 'stop_bid': stop_bid,
        'target_bid': target_bid, 'exit_net': exit_net, 'risk_points_net': risk,
        'atr14': atr, 'rr_cfg': c.rr, 'r': float(pnl / risk), 'exit_reason': reason,
        'spread_assumed': spread, 'slip_side': slip, 'stress': bool(stress),
    }
    return trade, exit_i + 1


def run_candidate(df: pd.DataFrame, c: Candidate, stress: bool = False) -> pd.DataFrame:
    rows: list[dict] = []
    for _, raw_day in df.groupby('ny_date', sort=True):
        day = raw_day.sort_values('time').reset_index(drop=True)
        i = 0
        last_entry = None
        used_sides: set[str] = set()
        n = 0
        while i < len(day) - 1 and n < MAX_TRADES_DAY:
            r = day.loc[i]
            if int(r.minute) < SIGNAL_START or int(r.minute) > SIGNAL_END:
                i += 1
                continue
            side = pullback_signal(r, c.family) if c.family.startswith('PB') else sweep_signal(r, c, used_sides)
            if side is None:
                i += 1
                continue
            next_time = day.loc[i + 1].time
            if last_entry is not None and (next_time - last_entry).total_seconds() < COOLDOWN_MIN * 60:
                i += 1
                continue
            trade, next_i = simulate_trade(day, i, c, side, stress)
            if trade is None:
                i += 1
                continue
            rows.append(trade)
            last_entry = day.loc[i + 1].time
            if c.family.startswith('SWEEP'):
                used_sides.add(side)
            n += 1
            i = max(next_i, i + 1)
    return pd.DataFrame(rows)


def pf(a: np.ndarray):
    pos = a[a > 0].sum()
    neg = -a[a < 0].sum()
    return float(pos / neg) if neg > 0 else (1e9 if pos > 0 else None)


def stats(t: pd.DataFrame) -> dict:
    if t.empty:
        return {'n': 0, 'mean': None, 'sum': 0.0, 'pf': None, 'win_rate': None, 'max_dd': None}
    a = t.r.to_numpy(float)
    eq = np.cumsum(a)
    peaks = np.maximum.accumulate(np.r_[0.0, eq])[:-1]
    dd = np.maximum(peaks - eq, 0.0)
    return {'n': int(len(a)), 'mean': float(a.mean()), 'sum': float(a.sum()), 'pf': pf(a),
            'win_rate': float((a > 0).mean()), 'max_dd': float(dd.max(initial=0.0))}


def by_year(t: pd.DataFrame) -> dict:
    if t.empty:
        return {}
    z = t.copy()
    z['year'] = pd.to_datetime(z.date).dt.year
    return {str(k): stats(g) for k, g in z.groupby('year')}


def month_rate(t: pd.DataFrame) -> tuple[float, int]:
    if t.empty:
        return 0.0, 0
    z = t.copy()
    z['month'] = pd.to_datetime(z.date).dt.to_period('M').astype(str)
    sums = z.groupby('month').r.sum()
    return float((sums > 0).mean()), int(len(sums))


def halves(t: pd.DataFrame) -> dict:
    if t.empty:
        return {'H1': 0.0, 'H2': 0.0}
    d = pd.to_datetime(t.date)
    return {'H1': float(t.loc[d.dt.month <= 6, 'r'].sum()),
            'H2': float(t.loc[d.dt.month >= 7, 'r'].sum())}


def bootstrap_p05_mean(t: pd.DataFrame, nrep: int = 5000, block: int = 20) -> float | None:
    a = t.r.to_numpy(float)
    if len(a) < block:
        return None
    rng = np.random.default_rng(BOOT_SEED)
    means = np.empty(nrep)
    max_start = len(a) - block
    need = math.ceil(len(a) / block)
    for k in range(nrep):
        starts = rng.integers(0, max_start + 1, size=need)
        sample = np.concatenate([a[s:s + block] for s in starts])[:len(a)]
        means[k] = sample.mean()
    return float(np.quantile(means, 0.05))


def dev_gate(primary: pd.DataFrame, stress_t: pd.DataFrame, sessions: int) -> tuple[bool, dict]:
    p = stats(primary)
    s = stats(stress_t)
    ys = by_year(primary)
    mr, nm = month_rate(primary)
    boot = bootstrap_p05_mean(primary)
    means = [v['mean'] for v in ys.values() if v['mean'] is not None]
    worst = min(means) if means else None
    positive_years = sum(1 for v in ys.values() if v['sum'] > 0)
    rps = p['sum'] / sessions if sessions else 0.0
    srps = s['sum'] / sessions if sessions else 0.0
    gates = {
        'n_ge_250': p['n'] >= 250,
        'mean_ge_0_15': p['mean'] is not None and p['mean'] >= 0.15,
        'pf_ge_1_30': p['pf'] is not None and p['pf'] >= 1.30,
        'r_per_session_ge_0_35': rps >= 0.35,
        'maxdd_le_12': p['max_dd'] is not None and p['max_dd'] <= 12.0,
        'positive_years_ge_2': positive_years >= 2,
        'worst_year_mean_ge_0': worst is not None and worst >= 0.0,
        'positive_month_rate_ge_58pct': mr >= 0.58,
        'stress_mean_gt_0': s['mean'] is not None and s['mean'] > 0.0,
        'stress_pf_ge_1_15': s['pf'] is not None and s['pf'] >= 1.15,
        'stress_r_per_session_ge_0_15': srps >= 0.15,
        'bootstrap_p05_mean_ge_0': boot is not None and boot >= 0.0,
    }
    detail = {'primary': p, 'stress': s, 'yearly': ys, 'sessions': sessions,
              'r_per_session': float(rps), 'stress_r_per_session': float(srps),
              'positive_years': positive_years, 'worst_year_mean': worst,
              'positive_month_rate': mr, 'active_months': nm,
              'bootstrap_p05_mean': boot, 'gates': gates}
    return all(gates.values()), detail


def robustness_score(d: dict) -> float:
    return float(2.0 * d['worst_year_mean'] + 1.5 * d['stress_r_per_session'] +
                 d['r_per_session'] + 0.5 * d['primary']['mean'] -
                 0.02 * d['primary']['max_dd'])


def validation_gate(primary: pd.DataFrame, stress_t: pd.DataFrame, sessions: int) -> tuple[bool, dict]:
    p = stats(primary)
    s = stats(stress_t)
    mr, nm = month_rate(primary)
    h = halves(primary)
    boot = bootstrap_p05_mean(primary)
    rps = p['sum'] / sessions if sessions else 0.0
    srps = s['sum'] / sessions if sessions else 0.0
    gates = {
        'n_ge_70': p['n'] >= 70,
        'mean_ge_0_15': p['mean'] is not None and p['mean'] >= 0.15,
        'pf_ge_1_30': p['pf'] is not None and p['pf'] >= 1.30,
        'r_per_session_ge_0_40': rps >= 0.40,
        'maxdd_le_10': p['max_dd'] is not None and p['max_dd'] <= 10.0,
        'stress_mean_gt_0': s['mean'] is not None and s['mean'] > 0.0,
        'stress_pf_ge_1_15': s['pf'] is not None and s['pf'] >= 1.15,
        'stress_r_per_session_ge_0_18': srps >= 0.18,
        'h1_positive': h['H1'] > 0.0,
        'h2_positive': h['H2'] > 0.0,
        'positive_month_rate_ge_58pct': mr >= 0.58,
        'bootstrap_p05_mean_ge_0': boot is not None and boot >= 0.0,
    }
    detail = {'primary': p, 'stress': s, 'sessions': sessions,
              'r_per_session': float(rps), 'stress_r_per_session': float(srps),
              'half_sums': h, 'positive_month_rate': mr, 'active_months': nm,
              'bootstrap_p05_mean': boot, 'gates': gates}
    return all(gates.values()), detail


def qa_year(m5: pd.DataFrame, year: int) -> dict:
    y = m5[m5.time.dt.year == year]
    morning = y[(y.minute >= SIGNAL_START) & (y.minute <= SIGNAL_END)]
    sessions = int(morning[morning.minute == SIGNAL_START].ny_date.nunique())
    bad = int(((y.low > y.high) | (y.open < y.low) | (y.open > y.high) |
               (y.close < y.low) | (y.close > y.high)).sum())
    return {'year': year, 'm5_rows': int(len(y)), 'first': str(y.time.min()),
            'last': str(y.time.max()), 'duplicates': int(y.duplicated('time').sum()),
            'ohlc_violations': bad, 'morning_sessions': sessions,
            'price_min': float(y.low.min()) if len(y) else None,
            'price_max': float(y.high.max()) if len(y) else None}


def main() -> None:
    raw_parts = [load_year(y) for y in ALL_YEARS]
    raw = pd.concat(raw_parts, ignore_index=True).sort_values('time').drop_duplicates('time').reset_index(drop=True)
    m5 = build_features(raw)
    qa = {str(y): qa_year(m5, y) for y in ALL_YEARS}

    dev = m5[m5.time.dt.year.isin(DEV_YEARS)].copy().reset_index(drop=True)
    val = m5[m5.time.dt.year == VAL_YEAR].copy().reset_index(drop=True)
    dev_sessions = sum(qa[str(y)]['morning_sessions'] for y in DEV_YEARS)
    val_sessions = qa[str(VAL_YEAR)]['morning_sessions']

    dev_results: dict[str, dict] = {}
    cand_map = {c.name: c for c in candidates()}
    for c in candidates():
        p = run_candidate(dev, c, stress=False)
        s = run_candidate(dev, c, stress=True)
        ok, detail = dev_gate(p, s, dev_sessions)
        detail.update({'candidate': asdict(c), 'name': c.name, 'eligible': ok,
                       'robustness_score': robustness_score(detail) if ok else None})
        dev_results[c.name] = detail

    selected: dict[str, str | None] = {}
    for fam in ('PB_LONG', 'PB_BI', 'SWEEP_LONG', 'SWEEP_BI'):
        eligible = [d for d in dev_results.values() if d['candidate']['family'] == fam and d['eligible']]
        selected[fam] = max(eligible, key=lambda x: x['robustness_score'])['name'] if eligible else None

    validation: dict[str, dict] = {}
    val_traces: list[pd.DataFrame] = []
    for fam, name in selected.items():
        if name is None:
            validation[fam] = {'status': 'DEV_FAMILY_REJECTED_NO_VALIDATION', 'selected': None}
            continue
        c = cand_map[name]
        p = run_candidate(val, c, stress=False)
        s = run_candidate(val, c, stress=True)
        ok, detail = validation_gate(p, s, val_sessions)
        detail['selected'] = name
        detail['status'] = 'VALIDATION_PASS_READY_TO_FREEZE_FOR_2025_OOS' if ok else 'VALIDATION_NO_GO'
        validation[fam] = detail
        if not p.empty:
            z = p.copy(); z['stage'] = 'VALIDATION_2024_PRIMARY'; val_traces.append(z)
        if not s.empty:
            z = s.copy(); z['stage'] = 'VALIDATION_2024_STRESS'; val_traces.append(z)

    result = {
        'status': 'XAU_V3_DEV_VALIDATION_COMPLETE_2025_UNOPENED',
        'hard_constraint': 'ZERO_PAID_EXTERNAL_DATA_REQUIRED_LIVE',
        'source': 'Public tiumbj/M1_XAUUSD files; format/time convention matches HistData MT M1 Bid bars',
        'cost_model': {
            'PRIMARY': {'spread_usd': 0.30, 'commission_notional_pct_per_side': 0.0007, 'slippage_usd_per_side': 0.0},
            'STRESS': {'spread_usd': 0.50, 'commission_notional_pct_per_side': 0.0007, 'slippage_usd_per_side': 0.05},
        },
        'partitions': {'DEV': '2021-2023', 'VALIDATION': '2024', 'OOS_2025': 'SEALED_NOT_DOWNLOADED'},
        'data_qa': qa, 'dev_sessions': dev_sessions, 'validation_sessions': val_sessions,
        'candidate_count': len(candidates()), 'dev_results': dev_results,
        'selected_by_family': selected, 'validation': validation,
        'oos_2025_opened': False,
        'notes': [
            'V3 code refuses any request for year >= 2025.',
            'No paid market-data subscription is required by any V3 family.',
            'A proxy pass remains subject to unchanged FTMO Free Trial/demo native Bid/Ask validation.'
        ]
    }
    (OUT / 'RESULT.json').write_text(json.dumps(result, indent=2, allow_nan=False, default=str))

    screen_rows = []
    for d in dev_results.values():
        screen_rows.append({
            'name': d['name'], 'family': d['candidate']['family'], 'eligible': d['eligible'],
            'n': d['primary']['n'], 'mean': d['primary']['mean'], 'pf': d['primary']['pf'],
            'r_per_session': d['r_per_session'], 'max_dd': d['primary']['max_dd'],
            'stress_mean': d['stress']['mean'], 'stress_pf': d['stress']['pf'],
            'stress_r_per_session': d['stress_r_per_session'],
            'worst_year_mean': d['worst_year_mean'], 'positive_month_rate': d['positive_month_rate'],
            'bootstrap_p05_mean': d['bootstrap_p05_mean'], 'score': d['robustness_score']})
    pd.DataFrame(screen_rows).to_csv(OUT / 'DEV_SCREEN.csv', index=False)
    if val_traces:
        pd.concat(val_traces, ignore_index=True).to_csv(OUT / 'VALIDATION_TRADES.csv', index=False)

    print(json.dumps({'status': result['status'], 'selected': selected, 'validation': validation},
                     indent=2, allow_nan=False, default=str))


if __name__ == '__main__':
    main()
