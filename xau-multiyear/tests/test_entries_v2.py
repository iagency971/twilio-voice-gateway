import numpy as np
import pandas as pd

from rzr.entries_v2 import build_entry, simulate_one


def _bars(n=60):
    idx=pd.date_range('2025-01-01',periods=n,freq='min',tz='UTC')
    b=pd.DataFrame(index=idx); base=np.full(n,100.0)
    for side,off in [('bid',0.0),('ask',0.2)]:
        cl=base+off
        b[f'open_{side}']=cl.copy(); b[f'high_{side}']=cl.copy()+0.05
        b[f'low_{side}']=cl.copy()-0.05; b[f'close_{side}']=cl.copy()
    b['open']=(b.open_bid+b.open_ask)/2; b['high']=(b.high_bid+b.high_ask)/2
    b['low']=(b.low_bid+b.low_ask)/2; b['close']=(b.close_bid+b.close_ask)/2
    b['spread']=0.2; b['quote_active']=True
    return b


def test_clean_rejection_pullback_fills_proximal_edge():
    b=_bars()
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='CLEAN_REJECTION',first_reclaim_minutes_v2=2)
    b.iloc[8,b.columns.get_loc('low_ask')]=100.05
    b.iloc[9,b.columns.get_loc('low_ask')]=99.95
    x=build_entry(r,b,'RECLAIM_PULLBACK')
    assert x and x['entry_idx']==9 and x['direction']=='LONG' and x['entry_price']==100.0
    assert x['stop_price'] < 99.5 and x['intrabar_limit_entry']


def test_failed_auction_pullback_uses_sweep_extreme_stop():
    b=_bars(); b.iloc[6,b.columns.get_loc('low')]=99.0
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='FAILED_AUCTION',reclaim_after_breach_minutes_v2=3,first_reclaim_minutes_v2=3)
    b.iloc[9,b.columns.get_loc('low_ask')]=99.95
    x=build_entry(r,b,'RECLAIM_PULLBACK')
    assert x and x['entry_idx']==9 and abs(x['stop_price']-98.6)<1e-9


def test_pullback_cancels_if_invalidated_before_fill():
    b=_bars()
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='CLEAN_REJECTION',first_reclaim_minutes_v2=2)
    b.iloc[8,b.columns.get_loc('low_bid')]=99.0
    b.iloc[8,b.columns.get_loc('low_ask')]=100.1
    assert build_entry(r,b,'RECLAIM_PULLBACK') is None


def test_pullback_same_bar_fill_and_stop_is_loss():
    b=_bars()
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='CLEAN_REJECTION',first_reclaim_minutes_v2=2)
    # Minute 8 both fills the 100.0 limit and spans above the 1R TP while also below the stop.
    # The simulator must resolve this ambiguous M1 bar adversarially as SL.
    b.iloc[8,b.columns.get_loc('low_ask')]=99.9
    b.iloc[8,b.columns.get_loc('low_bid')]=99.0
    b.iloc[8,b.columns.get_loc('high_bid')]=101.0
    b.iloc[8,b.columns.get_loc('high_ask')]=101.2
    x=build_entry(r,b,'RECLAIM_PULLBACK')
    assert x and x['entry_idx']==8
    s=simulate_one(x,b,1.0)
    assert s['result']=='SL' and s['ambiguous_same_bar']
