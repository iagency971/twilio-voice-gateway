from rzr.entries_s1 import apply_volatility_floor

def test_long_floor_only_widens():
    e=dict(direction='LONG',entry_price=100.0,stop_price=99.7,risk_price=.3,sigma60=2.0)
    x=apply_volatility_floor(e,.25)
    assert abs(x['risk_price']-.5)<1e-12 and abs(x['stop_price']-99.5)<1e-12 and x['s1_widened']

def test_short_floor_only_widens():
    e=dict(direction='SHORT',entry_price=100.0,stop_price=100.2,risk_price=.2,sigma60=2.0)
    x=apply_volatility_floor(e,.5)
    assert abs(x['risk_price']-1.0)<1e-12 and abs(x['stop_price']-101.0)<1e-12

def test_does_not_tighten_structural_stop():
    e=dict(direction='LONG',entry_price=100.0,stop_price=98.0,risk_price=2.0,sigma60=1.0)
    x=apply_volatility_floor(e,1.0)
    assert x['stop_price']==98.0 and x['risk_price']==2.0 and not x['s1_widened']
