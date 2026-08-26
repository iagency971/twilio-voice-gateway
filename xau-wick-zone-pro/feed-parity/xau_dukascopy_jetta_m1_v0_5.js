import fs from 'fs';
import path from 'path';
import {getHistoricalRates} from 'dukascopy-node';

function args(){
  const a={};for(let i=2;i<process.argv.length;i+=2)a[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
  for(const k of ['from','to','out','meta'])if(!a[k])throw new Error('missing --'+k);return a;
}
function normalizeRow(r){
  if(Array.isArray(r))return {timestamp:Number(r[0]),open:Number(r[1]),high:Number(r[2]),low:Number(r[3]),close:Number(r[4])};
  return {timestamp:Number(r.timestamp),open:Number(r.open),high:Number(r.high),low:Number(r.low),close:Number(r.close)};
}
async function one(side,a){
  let d=await getHistoricalRates({
    instrument:'xauusd',
    dates:{from:new Date(a.from),to:new Date(a.to)},
    timeframe:'m1',priceType:side,format:'json',utcOffset:0,volumes:false,ignoreFlats:true,
    batchSize:5,pauseBetweenBatchesMs:300,retryCount:3,pauseBetweenRetriesMs:500,retryOnEmpty:true
  });
  if(typeof d==='string')d=JSON.parse(d);
  if(!Array.isArray(d))throw new Error(side+' non-array response');
  const x=d.map(normalizeRow).filter(r=>Number.isFinite(r.timestamp)&&Number.isFinite(r.open)&&Number.isFinite(r.high)&&Number.isFinite(r.low)&&Number.isFinite(r.close));
  x.sort((p,q)=>p.timestamp-q.timestamp);
  const m=new Map();for(const r of x)m.set(r.timestamp,r);
  return [...m.values()];
}
(async()=>{
  const a=args();const bid=await one('bid',a);const ask=await one('ask',a);
  const B=new Map(bid.map(r=>[r.timestamp,r])),A=new Map(ask.map(r=>[r.timestamp,r]));
  const ts=[...B.keys()].filter(t=>A.has(t)).sort((x,y)=>x-y);
  const lines=['timestamp,open,high,low,close,open_bid,high_bid,low_bid,close_bid,open_ask,high_ask,low_ask,close_ask,spread'];
  for(const t of ts){const b=B.get(t),q=A.get(t);lines.push([
    new Date(t).toISOString(),(b.open+q.open)/2,(b.high+q.high)/2,(b.low+q.low)/2,(b.close+q.close)/2,
    b.open,b.high,b.low,b.close,q.open,q.high,q.low,q.close,q.close-b.close].join(','));}
  fs.mkdirSync(path.dirname(a.out),{recursive:true});fs.writeFileSync(a.out,lines.join('\n')+'\n');
  const meta={status:ts.length?'PASS':'EMPTY',source:'Dukascopy Jetta via dukascopy-node',package_version:'1.50.0',instrument:'xauusd',timeframe:'m1',price_types:['bid','ask'],ignoreFlats:true,utcOffset:0,from:a.from,to:a.to,bid_rows:bid.length,ask_rows:ask.length,common_rows:ts.length,first_timestamp_utc:ts.length?new Date(ts[0]).toISOString():null,last_timestamp_utc:ts.length?new Date(ts[ts.length-1]).toISOString():null,mid:'barwise average BID/ASK',local_gap_fill:false};
  fs.writeFileSync(a.meta,JSON.stringify(meta,null,2));console.log(JSON.stringify(meta,null,2));
})().catch(e=>{console.error(e&&e.stack||e);process.exit(1)});
