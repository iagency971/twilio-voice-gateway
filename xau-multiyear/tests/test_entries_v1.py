import numpy as np
import pandas as pd

from rzr.entries_v1 import build_entry, simulate_one


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


def test_failed_auction_stop_uses_sweep_extreme():
    b=_bars(); b.iloc[6,b.columns.get_loc('low')]=99.2
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='FAILED_AUCTION',reclaim_after_breach_minutes_v2=3,first_reclaim_minutes_v2=3)
    x=build_entry(r,b,'FAILED_AUCTION')
    assert x and x['direction']=='LONG' and abs(x['stop_price']-98.8)<1e-9


def test_clean_rejection_enters_next_open():
    b=_bars()
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='CLEAN_REJECTION',first_reclaim_minutes_v2=2)
    x=build_entry(r,b,'CLEAN_REJECTION')
    assert x['entry_idx']==8 and x['direction']=='LONG'


def test_accepted_support_flips_short_on_retest():
    b=_bars()
    for j in range(10,12):
        b.iloc[j,b.columns.get_loc('high_bid')]=99.4
        b.iloc[j,b.columns.get_loc('low_bid')]=99.2
        b.iloc[j,b.columns.get_loc('open_bid')]=99.3
        b.iloc[j,b.columns.get_loc('close_bid')]=99.3
    b.iloc[12,b.columns.get_loc('high_bid')]=99.6
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1,
           behavior_v2='ACCEPTED_BREAK')
    x=build_entry(r,b,'ACCEPTANCE_RETEST',acceptance_minutes=5,retest_minutes=30)
    assert x and x['direction']=='SHORT' and x['entry_idx']==12 and x['entry_price']==99.5
    assert x['stop_price']>100.0 and x['intrabar_limit_entry']


def test_same_bar_tp_sl_is_loss():
    b=_bars()
    entry=dict(direction='LONG',entry_idx=10,entry_price=100.2,stop_price=99.2,risk_price=1.0)
    b.iloc[11,b.columns.get_loc('low_bid')]=99.0
    b.iloc[11,b.columns.get_loc('high_bid')]=102.0
    s=simulate_one(entry,b,1.0)
    assert s['result']=='SL' and s['ambiguous_same_bar']


def test_touch_next_open_uses_ask_for_long():
    b=_bars()
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1)
    x=build_entry(r,b,'TOUCH_NEXT_OPEN')
    assert abs(x['entry_price']-100.2)<1e-9


def test_passive_touch_requires_executable_quote_at_zone_centre():
    b=_bars()
    r=dict(contact_idx=5,lower=99.5,upper=100.0,sigma60=1.0,side='SUPPORT',approach_direction=-1)
    # Centre=99.75, but ASK low is 100.15, so no fill until minute 9.
    b.iloc[9,b.columns.get_loc('low_ask')]=99.70
    x=build_entry(r,b,'PASSIVE_TOUCH')
    assert x and x['entry_idx']==9 and x['entry_price']==99.75 and x['intrabar_limit_entry']


def test_intrabar_limit_ignores_same_bar_tp_but_honors_stop():
    b=_bars()
    entry=dict(direction='LONG',entry_idx=10,entry_price=100.0,stop_price=99.0,risk_price=1.0,intrabar_limit_entry=True)
    b.iloc[10,b.columns.get_loc('high_bid')]=102.0
    b.iloc[10,b.columns.get_loc('low_bid')]=98.8
    out=simulate_one(entry,b,1.0)
    assert out['result']=='SL'
    b=_bars()
    b.iloc[10,b.columns.get_loc('high_bid')]=102.0
    out=simulate_one(entry,b,1.0)
    assert not (out['result']=='TP' and out['exit_idx']==10)
