#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import databento as db

NY = ZoneInfo('America/New_York')
DATASET = 'GLBX.MDP3'
SCHEMA = 'ohlcv-1m'


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_dbn(path: Path) -> pd.DataFrame:
    x = db.DBNStore.from_file(path).to_df().reset_index(drop=False)
    if 'ts_event' not in x.columns:
        x = x.rename(columns={x.columns[0]: 'ts_event'})
    x['ts_event'] = pd.to_datetime(x.ts_event, utc=True)
    return x.sort_values('ts_event').reset_index(drop=True)


def assign_gc_session(ctx: pd.DataFrame) -> pd.DataFrame:
    x = ctx.copy()
    local = x.ts_event.dt.tz_convert(NY)
    mod = local.dt.hour * 60 + local.dt.minute
    base = local.dt.normalize().dt.tz_localize(None)
    trade = base + pd.to_timedelta((mod >= 1080).astype(int), unit='D')
    pre = trade < pd.Timestamp('2015-09-21')
    close = pd.Series(1020, index=x.index)
    close.loc[pre.values] = 1035
    valid = (mod >= 1080) | (mod < close)
    x['gc_trade_date'] = trade.dt.date.astype(str)
    x['gc_session_valid'] = valid
    x.loc[~valid, 'gc_trade_date'] = ''
    return x


def session_bounds(date: str):
    d = pd.Timestamp(date)
    prev = (d - pd.Timedelta(1, unit='D')).date()
    start = pd.Timestamp(f'{prev} 18:00:00', tz=NY).tz_convert('UTC')
    close = '17:15:00' if d.date() < pd.Timestamp('2015-09-21').date() else '17:00:00'
    end = pd.Timestamp(f'{d.date()} {close}', tz=NY).tz_convert('UTC')
    return start, end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-levels', required=True)
    ap.add_argument('--context-dbn', required=True)
    ap.add_argument('--edge-overrides', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    source_path = Path(a.source_levels)
    context_path = Path(a.context_dbn)
    override_path = Path(a.edge_overrides)

    levels = pd.read_csv(source_path, dtype={'source_instrument_id': str})
    required = {'source_research_date','source_instrument_id','level_type','contact_tick_price'}
    missing = sorted(required - set(levels.columns))
    if missing:
        raise SystemExit(f'source registry missing required columns: {missing}')
    if len(levels) != 368 or levels.source_research_date.nunique() != 92:
        raise SystemExit(f'expected 368 levels / 92 source sessions, got {len(levels)} / {levels.source_research_date.nunique()}')
    if set(levels.level_type) != {'VWAP','POC','VAH','VAL'}:
        raise SystemExit('unexpected native level types')
    chk = levels.groupby('source_research_date').agg(levels=('level_type','size'), iids=('source_instrument_id','nunique'))
    if not ((chk.levels == 4) & (chk.iids == 1)).all():
        raise SystemExit('source-session level/instrument parity failure')

    ov = pd.read_csv(override_path, dtype=str).fillna('')
    ov_required = {'source_research_date','eligible_next_research_date','reason','evidence_primary','evidence_secondary'}
    if set(ov.columns) != ov_required:
        missing = sorted(ov_required - set(ov.columns))
        extra = sorted(set(ov.columns) - ov_required)
        raise SystemExit(f'edge override schema mismatch missing={missing} extra={extra}')
    if ov.source_research_date.duplicated().any():
        raise SystemExit('duplicate source_research_date in edge override')
    override_map = ov.set_index('source_research_date').eligible_next_research_date.to_dict()
    # V1 intentionally contains one calendar-only right-edge exception and nothing else.
    if override_map != {'2018-12-31':'2019-01-02'}:
        raise SystemExit(f'unexpected V1 edge override contents: {override_map}')

    ctx = assign_gc_session(load_dbn(context_path))
    valid = ctx[ctx.gc_session_valid & ctx.gc_trade_date.ne('')].copy()
    valid['volume'] = pd.to_numeric(valid.get('volume', 0), errors='coerce').fillna(0.0)
    session_stats = valid.groupby('gc_trade_date', sort=True).agg(
        bars=('ts_event','size'), total_volume=('volume','sum'), first_ts=('ts_event','min'), last_ts=('ts_event','max')
    ).reset_index()
    eligible_dates = [d for d,v,b in zip(session_stats.gc_trade_date, session_stats.total_volume, session_stats.bars) if b > 0 and v > 0]
    eligible_dates = sorted(set(eligible_dates))
    if not eligible_dates:
        raise SystemExit('no eligible GC auction sessions found in owned N0 context')

    session_rows = []
    used_overrides = []
    for source_date, g in levels.groupby('source_research_date', sort=True):
        source_date = str(source_date)
        later = [d for d in eligible_dates if d > source_date]
        if later:
            next_date = later[0]
            next_date_source = 'OWNED_N0_M1_POSITIVE_VOLUME_CALENDAR'
            if source_date in override_map:
                raise SystemExit(f'override unexpectedly unnecessary for {source_date}; owned context now resolves it')
        else:
            if source_date not in override_map:
                raise SystemExit(f'no later owned GC auction session and no frozen override for source date {source_date}')
            next_date = override_map[source_date]
            if next_date <= source_date:
                raise SystemExit(f'non-forward edge override {source_date}->{next_date}')
            next_date_source = 'FROZEN_CME_HOLIDAY_CALENDAR_EDGE_OVERRIDE_V1'
            used_overrides.append(source_date)
        iid = str(g.source_instrument_id.iloc[0])
        s,e = session_bounds(next_date)
        session_rows.append({
            'request_id': hashlib.sha256(f'NATIVE_N1|{source_date}|{next_date}|{iid}|{s.isoformat()}|{e.isoformat()}'.encode()).hexdigest()[:24],
            'request_type':'NATIVE_N1_RAW_OHLCV_SCREEN',
            'source_research_date':source_date,
            'eligible_next_research_date':next_date,
            'next_date_source':next_date_source,
            'source_instrument_id':iid,
            'dataset':DATASET,
            'schema':SCHEMA,
            'symbols':iid,
            'stype_in':'instrument_id',
            'start':s.isoformat(),
            'end':e.isoformat(),
            'source_level_count':int(len(g)),
            'source_level_types':'+'.join(sorted(g.level_type.astype(str))),
        })
    if used_overrides != ['2018-12-31']:
        raise SystemExit(f'expected exactly one used right-edge override, got {used_overrides}')

    req = pd.DataFrame(session_rows)
    if len(req) != 92 or req.request_id.nunique() != 92:
        raise SystemExit(f'expected 92 N1 source-session requests, got {len(req)} / {req.request_id.nunique()}')
    identity = ['source_instrument_id','start','end','schema']
    unique_market = req.drop_duplicates(identity).copy().reset_index(drop=True)
    unique_market['market_request_id'] = [hashlib.sha256(f"N1MKT|{r.source_instrument_id}|{r.start}|{r.end}|{r.schema}".encode()).hexdigest()[:24] for r in unique_market.itertuples()]
    market_map = unique_market.set_index(identity).market_request_id.to_dict()
    req['market_request_id'] = [market_map[(r.source_instrument_id,r.start,r.end,r.schema)] for r in req.itertuples()]

    client = db.Historical(os.environ['DATABENTO_API_KEY'])
    def quote(r):
        err = None
        for k in range(6):
            try:
                return float(client.metadata.get_cost(
                    dataset=r.dataset,
                    symbols=str(r.symbols),
                    stype_in=r.stype_in,
                    schema=r.schema,
                    start=r.start,
                    end=r.end,
                ))
            except Exception as z:
                err = z; time.sleep(min(10, 2 ** k))
        raise RuntimeError(err)

    costs = {}; errors = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        fs = {ex.submit(quote, r): r for r in unique_market.itertuples(index=False)}
        for f in as_completed(fs):
            r = fs[f]
            try:
                costs[str(r.market_request_id)] = f.result()
            except Exception as e:
                errors.append({'market_request_id':str(r.market_request_id),'source_instrument_id':str(r.source_instrument_id),'error':str(e)})
    if errors:
        raise SystemExit(f'N1 quote failures={len(errors)} {errors[:3]}')

    unique_market['cost_usd'] = unique_market.market_request_id.map(costs).astype(float)
    cost_map = unique_market.set_index('market_request_id').cost_usd.to_dict()
    req['market_request_cost_usd'] = req.market_request_id.map(cost_map).astype(float)
    total = float(unique_market.cost_usd.sum())

    req.to_csv(out/'native_n1_source_request_manifest.csv', index=False)
    unique_market.to_csv(out/'native_n1_market_request_manifest.csv', index=False)
    session_stats.to_csv(out/'owned_n0_session_calendar.csv', index=False)
    ov.to_csv(out/'frozen_edge_session_overrides_used.csv', index=False)
    source_sha = sha256_file(source_path)
    override_sha = sha256_file(override_path)
    req_sha = sha256_file(out/'native_n1_source_request_manifest.csv')
    market_sha = sha256_file(out/'native_n1_market_request_manifest.csv')
    manifest = {
        'version':'COMEX_DEV_RANK1_NATIVE_N1_QUOTE_V1_1',
        'authorization':'METADATA_ONLY',
        'download_performed':False,
        'market_data_download_performed':False,
        'dataset':DATASET,
        'schema':SCHEMA,
        'source_registry_version_required':'COMEX_DEV_RANK1_NATIVE_SOURCE_LEVELS_V1_1',
        'source_registry_sha256':source_sha,
        'edge_override_file_sha256':override_sha,
        'calendar_edge_override_count':len(used_overrides),
        'calendar_edge_overrides_used':used_overrides,
        'source_levels':int(len(levels)),
        'source_sessions':int(levels.source_research_date.nunique()),
        'source_requests':int(len(req)),
        'unique_market_requests':int(len(unique_market)),
        'exact_n1_cost_usd':total,
        'source_request_manifest_sha256':req_sha,
        'market_request_manifest_sha256':market_sha,
        'next_session_rule':'first later GC auction research date with positive-volume M1 records in already-owned GC.n.0 continuous context; one frozen calendar-only right-edge override 2018-12-31->2019-01-02 because owned context ends 2019-01-01; source price/outcome never used',
        'raw_instrument_rule':'same source_instrument_id that created terminal VWAP/POC/VAH/VAL; no continuous/cross-contract substitution',
        'screening_rule':'N1 OHLCV-1m can only eliminate impossible minutes; M1 crossing never confirms contact',
        'n2_rule':'exact raw trades only candidate minutes, quoted only after authorized N1 is downloaded; first exact trade at contact_tick_price is contact',
        'locked_blocks_opened':False,
        'dev_rank2_opened':False,
        'retro_confirm_opened':False,
        'locked_comex_test_opened':False,
        'notes':[
            'This workflow performs metadata.get_cost only.',
            'No Databento get_range or batch download is called.',
            'No N1 download is authorized by this manifest.',
            'No N2 trade-tape quote is possible until N1 reveals candidate minutes.'
        ]
    }
    (out/'native_n1_quote.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
