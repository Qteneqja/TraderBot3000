"""Predeclared, single-attempt diagnostic experiments; never model qualification."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from threadpoolctl import threadpool_limits

from app.backtesting.simulator import FillAssumptions
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.machine_learning.contracts import research_code_contract
from app.machine_learning.diagnostics import research_crash_trace
from app.machine_learning.policy import digest
from app.machine_learning.prospective import training_end
from app.machine_learning.registry import load_verified
from app.market_data.fingerprint import candle_manifest, verified_training_rows
from app.market_data.store import load_candles
from app.models.tables import Event, Instrument, ModelVersion
from app.research.forensics import diagnose_model, outcome_report, scan_outcomes
from app.strategies.registry import STRATEGIES


def implementation():
    return {'core': research_code_contract(), 'diagnostics': {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ('lab.py', 'forensics.py')}}


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def declare(db, label, root):
    settings = get_settings()
    if settings.demo_mode or settings.enable_live_trading or settings.trading_mode != 'PAPER':
        raise ValueError('Diagnostic research requires provider PAPER mode with live disabled')
    code = implementation()
    versions = list(db.scalars(select(ModelVersion)).all())
    selected = [v for v in versions if v.metadata_json.get('research_code') == code['core']
                and v.metadata_json.get('source') in ('oanda', 'coinbase')
                and v.metadata_json.get('evaluation_mode') == 'VALIDATION_ONLY'
                and v.metadata_json.get('horizon') == 12 and v.metadata_json.get('timeframe') == 300]
    scopes = []
    for symbol in sorted({v.metadata_json['symbol'] for v in selected}):
        models = [v for v in selected if v.metadata_json['symbol'] == symbol]
        meta = models[0].metadata_json
        if any(v.metadata_json['input_candles'] != meta['input_candles'] or
               v.metadata_json['costs'] != meta['costs'] for v in models):
            raise ValueError('Incompatible source manifests or costs require separately declared comparisons')
        first = datetime.fromisoformat(meta['input_candles']['start'])
        final = min(datetime.fromisoformat(v.metadata_json['partitions']['test'][0]) for v in models)
        final = training_end(db, symbol, meta['source'], first, final)
        rows = verified_training_rows(load_candles(db, symbol, 300, meta['source'], 1_000_000), meta['input_candles'])
        rows = [c for c in rows if c.time+timedelta(seconds=300) < final]
        instrument = db.get(Instrument, symbol)
        scopes.append({'symbol': symbol, 'source': meta['source'], 'timeframe': 300,
            'tick': str(instrument.tick_size), 'costs': meta['costs'], 'models': [v.id for v in models],
            'sealed_before': final.isoformat(), 'input_candles': candle_manifest(rows),
            'original_source_manifest': meta['input_candles']})
    if not scopes or not label.strip():
        raise ValueError('Label and currently compatible provider models are required')
    plan = {'schema': 'forensic-lab-v1', 'label': label, 'created_at': datetime.now(timezone.utc).isoformat(),
        'hypothesis': 'Measure label rarity, entry conditioning and raw/calibrated prediction compression before new fitting',
        'scopes': scopes, 'strategies': list(STRATEGIES), 'horizons': [12], 'code': code,
        'selection': 'All declared scopes and strategies; no threshold/policy search; global per-symbol final seal',
        'authority': 'DIAGNOSTIC_ONLY', 'limits': {'cpu_seconds': 1800, 'address_space_bytes': 4294967296,
                                                'native_threads': 1}}
    identifier = digest(plan)
    folder = Path(root)/identifier
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder/'plan.json', plan)
    db.add(Event(kind='quantitative_experiment_declared', detail={'id': identifier, 'label': label,
        'plan_sha256': identifier, 'code_sha256': code['core']['sha256'], 'execution_authority': False}))
    db.commit()
    return str(folder)


def run(db, folder):
    folder = Path(folder)
    plan = json.loads((folder/'plan.json').read_text())
    if digest(plan) != folder.name or plan['code'] != implementation() or plan['authority'] != 'DIAGNOSTIC_ONLY':
        raise ValueError('Experiment identity or implementation changed')
    with (folder/'claimed.json').open('x') as stream:
        json.dump({'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False}, stream)

    def stage(name, detail=None):
        with (folder/'stages.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                                     'stage': name, 'detail': detail or {}})+'\n')

    settings = get_settings()
    if settings.trading_mode != 'PAPER' or settings.demo_mode or settings.enable_live_trading:
        raise ValueError('Research runtime mode changed')
    import resource
    from decimal import Decimal

    resource.setrlimit(resource.RLIMIT_CPU, (plan['limits']['cpu_seconds'], plan['limits']['cpu_seconds']+10))
    resource.setrlimit(resource.RLIMIT_AS, (plan['limits']['address_space_bytes'], plan['limits']['address_space_bytes']))
    reports = []
    with research_crash_trace(folder.name, folder/'native-faults'), threadpool_limits(limits=1):
        for scope in plan['scopes']:
            stage('LOAD_PREFIX', {'symbol': scope['symbol']})
            start = datetime.fromisoformat(scope['input_candles']['start'])
            end = datetime.fromisoformat(scope['sealed_before'])
            if training_end(db, scope['symbol'], scope['source'], start, end) < end:
                raise ValueError('A new prospective reservation overlaps the declared diagnostic slice')
            rows = load_candles(db, scope['symbol'], 300, scope['source'], 1_000_000, start=start, end=end)
            rows = [c for c in rows if c.time+timedelta(seconds=300) < end]
            if candle_manifest(rows) != scope['input_candles']:
                raise ValueError('Declared diagnostic candles changed')
            costs = FillAssumptions(**{k: Decimal(v) for k, v in scope['costs'].items()})
            stage('SCAN_START', {'symbol': scope['symbol']})
            samples, counts = scan_outcomes(rows, Decimal(scope['tick']), costs, plan['strategies'], stage=stage)
            samples.to_parquet(folder/f"{scope['symbol']}-samples.parquet", index=False)
            summary = {'scope': scope, 'outcomes': outcome_report(samples, counts), 'models': []}
            stage('SCAN_COMPLETE', {'symbol': scope['symbol'], 'samples': len(samples)})
            for identifier in scope['models']:
                stage('MODEL_LOAD', {'model': identifier})
                version = db.get(ModelVersion, identifier)
                model = load_verified(version, Path(settings.model_artifact_dir))
                stage('MODEL_PREDICT', {'model': identifier})
                summary['models'].append(diagnose_model(version, model, samples))
                stage('MODEL_COMPLETE', {'model': identifier})
            write_json(folder/f"{scope['symbol']}-report.json", summary)
            reports.append(summary)
        catalog = [{'model': v.id, 'source': v.metadata_json.get('source'), 'status': v.status,
            'scope': 'CURRENT_DIAGNOSTIC' if v.metadata_json.get('research_code') == plan['code']['core'] else
                     'HISTORICAL_INCOMPATIBLE_OR_FIXTURE_METADATA_ONLY',
            'stored_validation': v.metadata_json.get('validation'),
            'stored_validation_probability_histogram': v.metadata_json.get('prediction_reference_validation_only')}
            for v in db.scalars(select(ModelVersion)).all()]
        result = {'schema': 'forensic-lab-report-v1', 'experiment': folder.name, 'plan': plan,
            'completed_at': datetime.now(timezone.utc).isoformat(), 'scopes': reports, 'model_catalog': catalog,
            'final_test': 'NOT_OPENED', 'execution_authority': False,
            'limitations': ['Candidate results overlap and are not portfolio returns.',
                'MFE/MAE includes the full exit-bar envelope, not an observed intrabar path.',
                'Quotes are modeled next-open bid/ask under declared constant costs, not observed executable history.',
                'Common per-symbol final seal can truncate diagnostic validation samples.',
                'Intervals are exploratory; no multiplicity-adjusted discovery or eligibility is claimed.']}
        write_json(folder/'result.json', result)
        stage('COMPLETED', {'execution_authority': False})
    return {'experiment': folder.name, 'status': 'COMPLETED', 'execution_authority': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('declare')
    p.add_argument('--label', required=True)
    p.add_argument('--root', default='data/reports/forensics')
    p = sub.add_parser('run')
    p.add_argument('folder')
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps({'folder': declare(db, args.label, args.root)} if args.command == 'declare' else run(db, args.folder)))
