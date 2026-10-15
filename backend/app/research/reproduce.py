"""Explicit bounded BTC native-failure reproduction; no registry publication or retry."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from threadpoolctl import threadpool_info, threadpool_limits

from app.backtesting.registered import evaluate_registered
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.machine_learning.candidate_training import CANDIDATE_FEATURES
from app.machine_learning.contracts import research_code_contract
from app.machine_learning.diagnostics import research_crash_trace
from app.machine_learning.policy import digest
from app.machine_learning.registry import load_verified
from app.machine_learning.training import estimator, scores
from app.models.tables import Event, ModelVersion
from app.research.lab import write_json


def declare(db, parent, root, version_id):
    parent = Path(parent)
    if not (parent/'result.json').is_file():
        raise ValueError('Complete the forensic outcome analysis before reproduction fits')
    version = db.get(ModelVersion, version_id)
    if version is None or version.metadata_json.get('symbol') != 'BTC-USD':
        raise ValueError('An existing preserved BTC artifact is required')
    cache = parent/'BTC-USD-samples.parquet'
    plan = {'schema': 'native-reproduction-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
        'hypothesis': 'Locate native failure in verified artifact load/predict, base/stress replay, or subsequent LightGBM fit/serialization',
        'parent_forensics': str(parent), 'model': version_id,
        'artifact_sha256': version.metadata_json['artifact_sha256'],
        'samples_sha256': hashlib.sha256(cache.read_bytes()).hexdigest(),
        'core': research_code_contract(), 'implementation': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'protocol': 'Two explicit single-thread LightGBM fit/calibration/serialization repetitions after one base/stress replay',
        'limits': {'cpu_seconds': 900, 'address_space_bytes': 4294967296, 'native_threads': 1},
        'automatic_retry': False, 'execution_authority': False}
    folder = Path(root)/digest(plan)
    folder.mkdir(parents=True, exist_ok=False)
    write_json(folder/'plan.json', plan)
    db.add(Event(kind='quantitative_reproduction_declared', detail={'id': folder.name, 'model': version_id,
        'hypothesis': plan['hypothesis'], 'execution_authority': False}))
    db.commit()
    return str(folder)


def run(db, folder):
    import resource
    from decimal import Decimal

    folder = Path(folder)
    plan = json.loads((folder/'plan.json').read_text())
    if digest(plan) != folder.name or plan['core'] != research_code_contract() or plan['implementation'] != hashlib.sha256(
            Path(__file__).read_bytes()).hexdigest():
        raise ValueError('Declared native reproduction changed')
    write_json(folder/'claimed.json', {'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retry': False})

    def stage(name, detail=None):
        with (folder/'stages.jsonl').open('a') as stream:
            stream.write(json.dumps({'stage': name, 'time': datetime.now(timezone.utc).isoformat(),
                                     'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                     'detail': detail or {}})+'\n')

    resource.setrlimit(resource.RLIMIT_CPU, (900, 910))
    resource.setrlimit(resource.RLIMIT_AS, (4294967296, 4294967296))
    settings = get_settings()
    version = db.get(ModelVersion, plan['model'])
    if settings.demo_mode or settings.trading_mode != 'PAPER' or version.metadata_json['artifact_sha256'] != plan['artifact_sha256']:
        raise ValueError('Reproduction context changed')
    cache = Path(plan['parent_forensics'])/'BTC-USD-samples.parquet'
    if hashlib.sha256(cache.read_bytes()).hexdigest() != plan['samples_sha256']:
        raise ValueError('Diagnostic samples changed')
    samples = pd.read_parquet(cache)
    samples = samples[samples.strategy == version.metadata_json['strategy']]
    parts = {key: samples[(samples.time >= pd.Timestamp(bounds[0])) & (samples.time <= pd.Timestamp(bounds[1]))]
             for key, bounds in version.metadata_json['partitions'].items() if key in ('train', 'calibration', 'validation')}
    for name in ('train', 'calibration'):
        if len(parts[name]) != version.metadata_json['sample_counts'][name]:
            raise ValueError('Fit/calibration reconstruction differs from the preserved model')
    if any(not np.isfinite(part[CANDIDATE_FEATURES].to_numpy()).all() for part in parts.values()):
        raise ValueError('Nonfinite diagnostic features')
    with research_crash_trace(folder.name, folder/'native-faults'), threadpool_limits(limits=1):
        stage('VERIFIED_LOGISTIC_LOAD')
        load_verified(version, Path(settings.model_artifact_dir))
        replays = {}
        for name, multiplier in (('BASE_REPLAY', Decimal(1)), ('STRESS_REPLAY', Decimal(2))):
            stage(name+'_START')
            replay = evaluate_registered(db, version.id, Path(settings.model_artifact_dir), settings, 'validation', multiplier)
            replays[name] = {k: v for k, v in replay['metrics'].items() if k not in ('equity_curve', 'drawdown_curve')}
            stage(name+'_COMPLETE', {'trades': replay['metrics']['trades']})
        fits = []
        for repeat in (1, 2):
            stage('LIGHTGBM_FIT_START', {'repeat': repeat})
            fitted = estimator('lightgbm').fit(parts['train'][CANDIDATE_FEATURES], parts['train'].label)
            stage('LIGHTGBM_CALIBRATION_START', {'repeat': repeat})
            calibrated = CalibratedClassifierCV(FrozenEstimator(fitted), method='sigmoid')
            calibrated.fit(parts['calibration'][CANDIDATE_FEATURES], parts['calibration'].label)
            predictions = calibrated.predict_proba(parts['validation'][CANDIDATE_FEATURES])
            path = folder/f'diagnostic-lightgbm-{repeat}.joblib'
            joblib.dump(calibrated, path)
            restored = joblib.load(path)
            if not np.array_equal(predictions, restored.predict_proba(parts['validation'][CANDIDATE_FEATURES])):
                raise ValueError('Serialization changed probabilities')
            fits.append({'repeat': repeat, 'validation': scores(parts['validation'].label.to_numpy(dtype=int), predictions),
                         'artifact_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            stage('LIGHTGBM_REPEAT_COMPLETE', {'repeat': repeat})
        result = {'schema': 'native-reproduction-result-v1', 'plan': plan, 'replays': replays, 'fits': fits,
            'feature_memory_bytes': int(samples[CANDIDATE_FEATURES].memory_usage(deep=True).sum()),
            'threadpools': threadpool_info(), 'status': 'NOT_REPRODUCED_UNDER_DECLARED_SINGLE_THREAD_LIMITS',
            'root_cause': 'UNRESOLVED: a successful bounded reproduction does not identify the past fault.',
            'execution_authority': False, 'completed_at': datetime.now(timezone.utc).isoformat()}
        write_json(folder/'result.json', result)
        stage('COMPLETED')
    return {'experiment': folder.name, 'status': result['status'], 'execution_authority': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('declare')
    p.add_argument('parent')
    p.add_argument('--root', default='/app/data/reports/native-reproductions')
    p.add_argument('--model', default='candidate-logistic-e2979ef54ebcefd8')
    p = sub.add_parser('run')
    p.add_argument('folder')
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps({'folder': declare(db, args.parent, args.root, args.model)} if args.command == 'declare' else run(db, args.folder)))
