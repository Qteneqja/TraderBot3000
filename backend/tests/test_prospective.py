"""Prospective orchestration: positive selection/coverage/labels are explicitly mocked."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
import test_paper_faults
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.machine_learning.candidate_training import CANDIDATE_FEATURES, EVENT_SCHEMA
from app.machine_learning.contracts import research_code_contract
from app.machine_learning.policy import acceptance_policy
from app.machine_learning.prospective import (
    abandon_period,
    evaluate_period,
    holdout_provenance,
    reserve_period,
    training_end,
    validation_evidence,
)
from app.machine_learning.registry import load_verified
from app.market_data.fingerprint import candle_manifest
from app.market_data.fixtures import demo_candles
from app.models.tables import FinalEvaluation, ModelVersion, OrderRow, PaperDeploymentSlot

store = test_paper_faults.store


class FrozenTestModel:
    classes_ = np.array([0, 1, 2])

    def fit(self, *args):
        raise AssertionError('Frozen final evaluation must not refit')

    def predict_proba(self, values):
        return np.tile([.2, .6, .2], (len(values), 1))


@pytest.fixture
def prospective(store, tmp_path, monkeypatch):
    engine, _, _, settings, now = store
    settings = settings.model_copy(update={'demo_mode': False})
    start = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=45)
    rows = [c.model_copy(update={'source': 'oanda'}) for c in demo_candles(count=100)]
    metadata = {'version': 'TEST-ONLY-frozen', 'symbol': 'EUR_USD', 'source': 'oanda', 'timeframe': 300,
        'strategy': 'trend', 'horizon': 12, 'tick': '.00001', 'input_candles': candle_manifest(rows),
        'dataset_sha256': 'test-only', 'event_schema': EVENT_SCHEMA, 'features': CANDIDATE_FEATURES,
        'evaluation_mode': 'VALIDATION_ONLY', 'research_code': research_code_contract(),
        'acceptance_policy': acceptance_policy(settings), 'coverage': {'research_ready': True},
        'walk_forward': [{'status': 'EVALUATED'}]*3,
        'costs': {'spread': '.0002', 'slippage': '.00001', 'fee_rate': '0', 'financing_per_bar': '0'},
        'partitions': {'train': ['test-only', 'test-only'], 'calibration': ['test-only', 'test-only'],
                       'validation': ['test-only', 'test-only'], 'test': ['sealed', 'sealed']},
        'sample_counts': {'train': 500, 'calibration': 200, 'validation': 200, 'test': 200},
        'validation': {}, 'class_frequency_baseline': {'validation': {}}}
    artifact = tmp_path / 'TEST-ONLY-frozen.joblib'
    joblib.dump({'model': FrozenTestModel(), 'report': metadata}, artifact)
    metadata = metadata | {'artifact_filename': artifact.name,
                           'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
    with Session(engine) as db:
        db.add(ModelVersion(id=metadata['version'], metadata_json=metadata, status='EXPERIMENTAL'))
        db.commit()
    monkeypatch.setattr('app.machine_learning.prospective.validation_evidence',
        lambda *args: {'validation': {'test_only_mock': True}, 'training_class_frequency': [1/3]*3})
    return engine, settings, now, start, end, tmp_path, rows, metadata


def reserve(db, value, parent='TEST-ONLY-frozen'):
    _, settings, now, start, end, root, _, _ = value
    return reserve_period(db, parent, root, settings, start, end, 'test-operator', 'Mock positive selection', now)


def test_reservation_is_future_immutable_unique_and_shared_across_models(prospective):
    engine, settings, now, start, end, root, _, metadata = prospective
    with Session(engine) as db:
        with pytest.raises(ValueError, match='future'):
            reserve_period(db, metadata['version'], root, settings, now-timedelta(days=1), end, 'test', 'test', now)
        identifier = reserve(db, prospective)
        assert db.get(FinalEvaluation, identifier).state == 'RESERVED'
        with pytest.raises(ValueError, match='already'):
            reserve(db, prospective)
        db.add(ModelVersion(id='TEST-ONLY-other', status='EXPERIMENTAL', metadata_json=metadata | {'version': 'TEST-ONLY-other'}))
        db.commit()
        with pytest.raises(ValueError, match='overlap'):
            reserve(db, prospective, 'TEST-ONLY-other')
        assert training_end(db, 'EUR_USD', 'oanda', now-timedelta(days=365), end+timedelta(days=1)) == start
        assert training_end(db, 'GBP_USD', 'oanda', now, end) == end
        with pytest.raises(ValueError, match='intersects'):
            training_end(db, 'EUR_USD', 'oanda', start+timedelta(days=1), end)
        row = db.get(FinalEvaluation, identifier)
        row.plan = row.plan | {'end': (end+timedelta(days=1)).isoformat()}
        db.commit()
        with pytest.raises(ValueError, match='changed'):
            training_end(db, 'EUR_USD', 'oanda', now, end)


def test_concurrent_reservations_cannot_create_two_final_tests(prospective):
    engine = prospective[0]

    def attempt(_):
        with Session(engine) as db:
            try:
                return reserve(db, prospective)
            except ValueError:
                return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(attempt, range(2)))
    assert sum(r is not None for r in results) == 1


def test_future_test_cannot_run_early_and_failure_is_consumed_once(prospective, monkeypatch):
    engine, settings, now, _, end, root, _, _ = prospective
    with Session(engine) as db:
        identifier = reserve(db, prospective)
        with pytest.raises(ValueError, match='incomplete'):
            evaluate_period(db, identifier, root, settings, now)
        assert db.get(FinalEvaluation, identifier).state == 'RESERVED'
        calls = []

        def outage(*args, **kwargs):
            calls.append(1)
            raise RuntimeError('mock provider/storage outage')

        monkeypatch.setattr('app.machine_learning.prospective.load_candles', outage)
        with pytest.raises(RuntimeError, match='outage'):
            evaluate_period(db, identifier, root, settings, end+timedelta(days=1))
        assert db.get(FinalEvaluation, identifier).state == 'FAILED'
        with pytest.raises(ValueError, match='already claimed'):
            evaluate_period(db, identifier, root, settings, end+timedelta(days=1))
        assert len(calls) == 1


def test_final_evaluation_uses_frozen_model_without_fitting_or_promotion(prospective, monkeypatch):
    engine, settings, _, start, end, root, rows, metadata = prospective
    future = [c.model_copy(update={'time': start+timedelta(seconds=300*i)}) for i, c in enumerate(rows)]
    sample = pd.DataFrame({key: np.zeros(100) for key in CANDIDATE_FEATURES})
    sample['time'] = [start+timedelta(seconds=300*i) for i in range(100)]
    sample['label'] = np.arange(100) % 3
    sample['net_r'] = 0.0
    monkeypatch.setattr('app.machine_learning.prospective.load_candles', lambda *a, **k: rows+future)
    monkeypatch.setattr('app.machine_learning.prospective.coverage_report', lambda *a, **k: {'research_ready': True})
    monkeypatch.setattr('app.machine_learning.prospective.dataset', lambda *a, **k: (sample, {}))
    def assessment(db, model_id, *args):
        final = db.get(ModelVersion, model_id)
        assert not holdout_provenance(db, final)  # Activation blocked while finalization is in progress.
        assert holdout_provenance(db, final, allow_evaluating=True)
        return {'review_id': 'TEST-ONLY-rejected-review', 'status': 'REJECTED', 'reasons': ['TEST_ONLY_MOCK']}

    monkeypatch.setattr('app.machine_learning.prospective.assess_model', assessment)
    with Session(engine) as db:
        identifier = reserve(db, prospective)
        result = evaluate_period(db, identifier, root, settings, end+timedelta(days=1))
        assert result['status'] == 'REJECTED' and result['refitted'] is False and not result['execution_authority']
        final = db.get(ModelVersion, result['model'])
        assert final.status == 'EXPERIMENTAL' and load_verified(final, Path(root)) is not None
        assert final.metadata_json['prospective_final']['frozen_parent_artifact_sha256'] == metadata['artifact_sha256']
        assert holdout_provenance(db, final)
        assert not holdout_provenance(db, ModelVersion(id='forged', metadata_json=final.metadata_json))
        # Consumed holdout history may train later candidates, whose FINAL period must be new.
        assert training_end(db, 'EUR_USD', 'oanda', start-timedelta(days=365), end+timedelta(days=2)) == end+timedelta(days=2)
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0
        assert db.scalar(select(func.count()).select_from(PaperDeploymentSlot)) == 0
        assert db.get(ModelVersion, metadata['version']).metadata_json == metadata
        with pytest.raises(ValueError, match='already claimed'):
            evaluate_period(db, identifier, root, settings, end+timedelta(days=1))


def test_real_validation_guard_rejects_missing_prerequisites(prospective):
    engine, settings, _, _, _, root, _, metadata = prospective
    with Session(engine) as db:
        parent = db.get(ModelVersion, metadata['version'])
        parent.metadata_json = metadata | {'sample_counts': {'calibration': 199}}
        with pytest.raises(ValueError, match='prerequisites'):
            validation_evidence(db, parent, root, settings)


def test_abandonment_cannot_restart_test_or_publish_stale_results(prospective, monkeypatch):
    engine, settings, _, _, end, root, _, _ = prospective
    with Session(engine) as db:
        identifier = reserve(db, prospective)

        def abandon_during_read(*args, **kwargs):
            with Session(engine) as operator:
                abandon_period(operator, identifier, 'test-operator', 'Permanent abandonment test')
            raise RuntimeError('mock interrupted evaluation')

        monkeypatch.setattr('app.machine_learning.prospective.load_candles', abandon_during_read)
        with pytest.raises(RuntimeError, match='interrupted'):
            evaluate_period(db, identifier, root, settings, end+timedelta(days=1))
        assert db.get(FinalEvaluation, identifier).state == 'ABANDONED'
        with pytest.raises(ValueError, match='already claimed'):
            evaluate_period(db, identifier, root, settings, end+timedelta(days=1))
