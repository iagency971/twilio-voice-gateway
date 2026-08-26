#!/usr/bin/env python3
from __future__ import annotations
import argparse,gzip,json,random,string,time
from datetime import datetime,timezone
import websocket


def args():
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    p.add_argument('--meta',required=True)
    p.add_argument('--target',type=int,default=100000)
    p.add_argument('--batch',type=int,default=5000)
    return p.parse_args()


def main():
    a=args();symbol='FOREXCOM:XAUUSD'
    def rid(p):return p+'_'+''.join(random.choice(string.ascii_lowercase) for _ in range(12))
    def pack(m,p):
        s=json.dumps({'m':m,'p':p},separators=(',',':'));return f'~m~{len(s)}~m~'+s
    ws=websocket.create_connection('wss://data.tradingview.com/socket.io/websocket?from=chart%2F',timeout=25,origin='https://www.tradingview.com',header=['User-Agent: Mozilla/5.0'])
    cs=rid('cs');qs=rid('qs')
    def send(m,p):ws.send(pack(m,p))
    send('set_auth_token',['unauthorized_user_token']);send('chart_create_session',[cs,'']);send('quote_create_session',[qs])
    send('quote_add_symbols',[qs,symbol,{'flags':['force_permission']}])
    send('resolve_symbol',[cs,'symbol_1','={"symbol":"FOREXCOM:XAUUSD","adjustment":"splits","session":"regular"}'])
    rows={}
    def collect(limit_s=40):
        start=time.time();before=len(rows)
        while time.time()-start<limit_s:
            msg=ws.recv()
            if isinstance(msg,str) and msg.startswith('~m~') and '~h~' in msg and msg.count('~m~')==2:
                try:ws.send(msg)
                except:pass
            if not isinstance(msg,str):continue
            for part in msg.split('~m~'):
                if not part or part.isdigit() or part.startswith('~h~'):continue
                try:obj=json.loads(part)
                except:continue
                m=obj.get('m');p=obj.get('p',[])
                if m=='timescale_update' and len(p)>=2 and isinstance(p[1],dict):
                    s=p[1].get('s1')
                    if isinstance(s,dict):
                        for rec in s.get('s',[]) or []:
                            v=rec.get('v') if isinstance(rec,dict) else None
                            if v and len(v)>=5 and v[0] is not None:
                                rows[int(v[0])]=[int(v[0]),v[1],v[2],v[3],v[4],v[5] if len(v)>5 else None]
                if m=='series_completed' and len(p)>=2 and p[0]==cs and p[1]=='s1':return len(rows)-before
        return -1
    send('create_series',[cs,'s1','s1','symbol_1','1',a.batch]);increments=[collect()];no_progress=0
    while len(rows)<a.target and no_progress<2:
        before=len(rows);send('request_more_data',[cs,'s1',a.batch]);increments.append(collect())
        no_progress=no_progress+1 if len(rows)<=before else 0;time.sleep(.2)
    ws.close();data=[rows[k] for k in sorted(rows)]
    if not data:raise RuntimeError('No FOREXCOM data returned')
    with gzip.open(a.output,'wt',newline='') as f:
        f.write('timestamp_utc,open,high,low,close,volume\n')
        for ts,o,h,l,c,v in data:
            t=datetime.fromtimestamp(ts,timezone.utc).isoformat().replace('+00:00','Z')
            f.write(f'{t},{o},{h},{l},{c},{"" if v is None else v}\n')
    meta={'status':'PASS' if len(data)>a.batch else 'LIMITED','symbol':symbol,'interval':'1','target_bars':a.target,'batch':a.batch,'received_unique_bars':len(data),'increments':increments,'first_timestamp_utc':datetime.fromtimestamp(data[0][0],timezone.utc).isoformat().replace('+00:00','Z'),'last_timestamp_utc':datetime.fromtimestamp(data[-1][0],timezone.utc).isoformat().replace('+00:00','Z'),'acquired_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'transport':'TradingView chart websocket / request_more_data','bar_source':'mid','purpose':'prospective v0.2 E-BUY entry transfer sample extension'}
    open(a.meta,'w').write(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))

if __name__=='__main__':main()
