"""Bounded entry/horizon ablations; separate research schemas, no production models."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd
from threadpoolctl import threadpool_limits

from app.backtesting.simulator import FillAssumptions
from app.database.session import SessionLocal
from app.indicators.features import align_higher, compute, frame
from app.machine_learning.contracts import research_code_contract
from app.machine_learning.diagnostics import research_crash_trace
from app.machine_learning.policy import digest
from app.machine_learning.prospective import training_end
from app.market_data.fingerprint import candle_manifest
from app.market_data.store import load_candles
from app.models.tables import Event
from app.research.forensics import scan_outcomes, summarize
from app.research.lab import write_json


def confirmation_masks(candles, samples, tick):
    """Current/prior completed bars and completed resampled hours only."""
    if samples.empty:
        return {'PULLBACK_HTF': pd.Series(False, index=samples.index),
                'BREAKOUT_RETEST': pd.Series(False, index=samples.index)}
    data = compute(frame(candles))
    hours = data.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
    hours = hours[data.close.resample('1h').count() == 12].dropna()
    higher = compute(hours)
    joined = align_higher(data, higher, 300, 3600).set_index('time')
    previous = data.shift(1)
    indexed = data.reindex(pd.DatetimeIndex(pd.to_datetime(samples.time, utc=True)-pd.Timedelta(seconds=300)))
    prior = previous.reindex(indexed.index)
    hour = joined.reindex(indexed.index).trend_higher
    long = samples.direction_name.to_numpy() == 'LONG'
    pull_long = (prior.close <= prior.ema_fast) & (indexed.close > indexed.ema_fast) & (indexed.rsi > prior.rsi) & (hour > 0)
    pull_short = (prior.close >= prior.ema_fast) & (indexed.close < indexed.ema_fast) & (indexed.rsi < prior.rsi) & (hour < 0)
    retest_long = (prior.close > prior.prior_high) & (indexed.low <= prior.prior_high+float(tick)) & (indexed.close > prior.prior_high)
    retest_short = (prior.close < prior.prior_low) & (indexed.high >= prior.prior_low-float(tick)) & (indexed.close < prior.prior_low)
    return {'PULLBACK_HTF': pd.Series((pull_long.to_numpy() & long) | (pull_short.to_numpy() & ~long), index=samples.index),
            'BREAKOUT_RETEST': pd.Series((retest_long.to_numpy() & long) | (retest_short.to_numpy() & ~long), index=samples.index)}


def declare(db, parent, root):
    parent = Path(parent)
    if not (parent/'result.json').is_file():
        raise ValueError('Completed forensic evidence is required before hypothesis ablations')
    forensic = json.loads((parent/'result.json').read_text())
    cases = [{'strategy': 'trend', 'filter': 'IMMEDIATE', 'horizon': h} for h in (6, 12, 24, 48)]
    cases += [{'strategy': 'trend', 'filter': 'PULLBACK_HTF', 'horizon': h} for h in (12, 48)]
    cases += [{'strategy': 'breakout', 'filter': f, 'horizon': h} for f in ('IMMEDIATE', 'BREAKOUT_RETEST') for h in (12, 48)]
    plan = {'schema': 'bounded-hypotheses-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
        'hypothesis': 'A longer causal holding window or completed-bar entry confirmation may improve rare target outcomes; no threshold search',
        'parent_experiment': parent.name, 'core': research_code_contract(),
        'implementation': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'forensic_helper': hashlib.sha256(Path(__file__).with_name('forensics.py').read_bytes()).hexdigest(),
        'scopes': [s['scope'] for s in forensic['scopes'] if s['scope']['symbol'] in ('EUR_USD', 'GBP_USD')],
        'cases': cases, 'case_count': 20, 'model_fits': 0, 'selection': 'Report every case and common-entry paired horizon subsets',
        'limits': {'cpu_seconds': 900, 'address_space_bytes': 4294967296, 'native_threads': 1},
        'execution_authority': False}
    folder = Path(root)/digest(plan)
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder/'plan.json', plan)
    db.add(Event(kind='quantitative_hypotheses_declared', detail={'id': folder.name,
        'case_count': 20, 'parent': parent.name, 'execution_authority': False}))
    db.commit()
    return str(folder)


def run(db, folder):
    import resource

    folder = Path(folder)
    plan = json.loads((folder/'plan.json').read_text())
    if (digest(plan) != folder.name or plan['core'] != research_code_contract()
        or plan['implementation'] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        or plan['forensic_helper'] != hashlib.sha256(Path(__file__).with_name('forensics.py').read_bytes()).hexdigest()):
        raise ValueError('Declared hypothesis implementation changed')
    write_json(folder/'claimed.json', {'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False})
    resource.setrlimit(resource.RLIMIT_CPU, (900, 910))
    resource.setrlimit(resource.RLIMIT_AS, (4294967296, 4294967296))
    results = []
    with research_crash_trace(folder.name, folder/'native-faults'), threadpool_limits(limits=1):
        for scope in plan['scopes']:
            start, end = datetime.fromisoformat(scope['input_candles']['start']), datetime.fromisoformat(scope['sealed_before'])
            if training_end(db, scope['symbol'], scope['source'], start, end) < end:
                raise ValueError('New reserved final period intersects research')
            rows = load_candles(db, scope['symbol'], 300, scope['source'], 1_000_000, start=start, end=end)
            rows = [r for r in rows if r.time+timedelta(seconds=300) < end]
            if candle_manifest(rows) != scope['input_candles']:
                raise ValueError('Declared research data changed')
            costs = FillAssumptions(**{k: Decimal(v) for k, v in scope['costs'].items()})
            horizons = {}
            for horizon in (6, 12, 24, 48):
                horizons[horizon], _ = scan_outcomes(rows, Decimal(scope['tick']), costs, ['trend', 'breakout'], horizon=horizon)
            common = set.intersection(*(set(part[part.strategy == 'trend'].candidate_id) for part in horizons.values()))
            for case in plan['cases']:
                samples = horizons[case['horizon']]
                subset = samples[samples.strategy == case['strategy']]
                if case['filter'] != 'IMMEDIATE':
                    subset = subset[confirmation_masks(rows, subset, Decimal(scope['tick']))[case['filter']]]
                results.append({'symbol': scope['symbol'], 'case': case,
                    'outcome_schema': f"research-{case['strategy']}-{case['filter'].lower()}-{case['horizon']}bars-v1",
                    'summary': summarize(subset),
                    'paired_common_horizon_subset': summarize(subset[subset.candidate_id.isin(common)])
                        if case['strategy'] == 'trend' and case['filter'] == 'IMMEDIATE' else None,
                    'execution_authority': False})
                with (folder/'stages.jsonl').open('a') as stream:
                    stream.write(json.dumps({'symbol': scope['symbol'], 'case': case, 'candidates': len(subset)})+'\n')
        result = {'schema': 'bounded-hypotheses-report-v1', 'plan': plan, 'cases': results,
            'completed_at': datetime.now(timezone.utc).isoformat(), 'final_test': 'NOT_OPENED',
            'execution_authority': False, 'model_fits': 0,
            'limitations': ['Twenty exploratory comparisons; no multiplicity-adjusted discovery or eligibility.',
                'Candidate returns overlap; no portfolio profit factor/drawdown or risk-approved order is inferred.',
                'Confirmation uses fixed causal research features; not a deployed entry policy.',
                'No limit-entry or trailing-stop execution is claimed.']}
        write_json(folder/'result.json', result)
    return {'experiment': folder.name, 'cases': len(results), 'execution_authority': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('declare')
    p.add_argument('parent')
    p.add_argument('--root', default='/app/data/reports/hypotheses')
    p = sub.add_parser('run')
    p.add_argument('folder')
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps({'folder': declare(db, args.parent, args.root)} if args.command == 'declare' else run(db, args.folder)))
