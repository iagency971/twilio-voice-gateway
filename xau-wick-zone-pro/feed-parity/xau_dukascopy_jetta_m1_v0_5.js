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
function utcDay(t){const d=new Date(t);return new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()));}
async function fetchDay(side,from,to){
  try{
    let d=await getHistoricalRates({
      instrument:'xauusd',dates:{from,to},timeframe:'m1',priceType:side,format:'json',utcOffset:0,volumes:false,ignoreFlats:true,
      batchSize:1,pauseBetweenBatchesMs:0,retryCount:3,pauseBetweenRetriesMs:500,retryOnEmpty:false
    });
    if(typeof d==='string')d=JSON.parse(d);
    if(!Array.isArray(d))throw new Error(side+' non-array response');
    return d.map(normalizeRow).filter(r=>Number.isFinite(r.timestamp)&&Number.isFinite(r.open)&&Number.isFinite(r.high)&&Number.isFinite(r.low)&&Number.isFinite(r.close));
  }catch(e){
    if(String(e&&e.message||e).toLowerCase().includes('empty dataset'))return [];
    throw e;
  }
}
async function one(side,a){
  const start=utcDay(a.from),stop=new Date(a.to);const rows=[];const days=[];
  for(let d=new Date(start);d<stop;d=new Date(d.getTime()+86400000)){
    const next=new Date(Math.min(d.getTime()+86400000,stop.getTime()));
    const q=await fetchDay(side,d,next);rows.push(...q);days.push({date:d.toISOString().slice(0,10),rows:q.length});
  }
  rows.sort((p,q)=>p.timestamp-q.timestamp);const m=new Map();for(const r of rows)m.set(r.timestamp,r);
  return {rows:[...m.values()],days};
}
(async()=>{
  const a=args();const br=await one('bid',a);const ar=await one('ask',a);const bid=br.rows,ask=ar.rows;
  const B=new Map(bid.map(r=>[r.timestamp,r])),A=new Map(ask.map(r=>[r.timestamp,r]));
  const ts=[...B.keys()].filter(t=>A.has(t)).sort((x,y)=>x-y);
  const lines=['timestamp,open,high,low,close,open_bid,high_bid,low_bid,close_bid,open_ask,high_ask,low_ask,close_ask,spread'];
  for(const t of ts){const b=B.get(t),q=A.get(t);lines.push([
    new Date(t).toISOString(),(b.open+q.open)/2,(b.high+q.high)/2,(b.low+q.low)/2,(b.close+q.close)/2,
    b.open,b.high,b.low,b.close,q.open,q.high,q.low,q.close,q.close-b.close].join(','));}
  fs.mkdirSync(path.dirname(a.out),{recursive:true});fs.writeFileSync(a.out,lines.join('\n')+'\n');
  const meta={status:ts.length?'PASS':'EMPTY',source:'Dukascopy Jetta via dukascopy-node',package_version:'1.50.0',instrument:'xauusd',timeframe:'m1',price_types:['bid','ask'],ignoreFlats:true,utcOffset:0,from:a.from,to:a.to,bid_rows:bid.length,ask_rows:ask.length,common_rows:ts.length,first_timestamp_utc:ts.length?new Date(ts[0]).toISOString():null,last_timestamp_utc:ts.length?new Date(ts[ts.length-1]).toISOString():null,mid:'barwise average BID/ASK',local_gap_fill:false,transport_chunking:'UTC day-by-day; empty day accepted as zero rows; no synthetic bars',bid_days:br.days,ask_days:ar.days};
  fs.writeFileSync(a.meta,JSON.stringify(meta,null,2));console.log(JSON.stringify(meta,null,2));
})().catch(e=>{console.error(e&&e.stack||e);process.exit(1)});
