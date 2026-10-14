"""Controlled research/outcome tests. Positive data/model eligibility is explicitly mocked."""

from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
import test_deployment
import test_paper_faults
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.machine_learning.learning import claim_run, queue_due, run_research, schedule_research, validate_plan
from app.machine_learning.monitoring import (
    approve_drift_policy,
    drift_policy,
    enforce_monitor,
    monitor_model,
    psi,
    wilson,
)
from app.machine_learning.outcomes import collect_outcomes
from app.machine_learning.policy import digest
from app.machine_learning.training import estimator
from app.models.tables import (
    Account,
    LearningRun,
    LearningSchedule,
    ModelVersion,
    OrderRow,
    SignalRow,
    TradeOutcome,
)

store = test_paper_faults.store
deployment_store = test_deployment.deployment_store


def plan():
    return {"schema": "learning-plan-v1", "symbol": "EUR_USD", "source": "oanda", "timeframe": 300,
            "strategy": "trend", "history_days": 365, "interval_days": 7, "families": ["logistic"],
            "costs": {"spread": ".0002", "slippage": ".00001", "fee_rate": "0", "financing_per_bar": "0"},
            "cost_evidence": "Explicit test-only simulated assumptions", "validation_only": True}


@pytest.mark.parametrize('family', ['logistic', 'random_forest', 'lightgbm', 'xgboost'])
def test_cpu_model_families_return_valid_three_class_probabilities(family):
    rng = np.random.default_rng(42)
    features = pd.DataFrame(rng.normal(size=(150, 4)), columns=list('abcd'))
    labels = np.tile(np.array([0, 1, 2]), 50)
    model = estimator(family).fit(features, labels)
    probabilities = model.predict_proba(features.iloc[:10])
    assert probabilities.shape == (10, 3)
    assert np.isfinite(probabilities).all() and (probabilities >= 0).all()
    np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)


def test_plan_cannot_request_auto_promotion_or_unsealed_test():
    for change in ({'validation_only': False}, {'families': ['unknown']}, {'interval_days': 0}, {'auto_activate': True}):
        with pytest.raises(ValueError):
            validate_plan(plan() | change)


def test_learning_summary_projects_candidate_fields_without_loading_curves(store):
    from app.main import learning_status

    engine, _, _, _, now = store
    with Session(engine) as db:
        schedule = schedule_research(db, plan(), 'operator', 'test', now, now)
        db.add(LearningRun(id='summary-test', schedule_id=schedule, scheduled_for=now, state='COMPLETED',
            result={'final_test': 'NOT_EVALUATED', 'candidates': [{'family': 'logistic', 'status': 'EXPERIMENTAL',
                'validation': {'multiclass_brier': .6}, 'portfolio': {'equity_curve': ['not-for-dashboard']*1000}}]}))
        db.commit()
        db.expunge_all()
        report = learning_status(db)
        assert report['runs'][0]['candidates'][0]['validation']['multiclass_brier'] == .6
        assert 'portfolio' not in report['runs'][0]['candidates'][0]
        assert not any(isinstance(obj, LearningRun) for obj in db.identity_map.values())


def test_scheduling_is_idempotent_coalesces_missed_weeks_and_claims_once(store):
    engine, _, _, _, now = store
    with Session(engine) as db:
        schedule = schedule_research(db, plan(), 'test-operator', 'mock research', now, now)
        assert schedule_research(db, plan(), 'test-operator', 'repeat', now, now) == schedule
        run_ids = queue_due(db, now + timedelta(days=22))
        assert len(run_ids) == 1 and queue_due(db, now + timedelta(days=22)) == []
        assert claim_run(db, run_ids[0], 'worker-a', now)
        assert not claim_run(db, run_ids[0], 'worker-b', now)
        assert db.get(LearningRun, run_ids[0]).worker_id == 'worker-a'
        assert db.scalar(select(func.count()).select_from(ModelVersion)) == 1  # Existing test-only registry seed.


def test_disabled_schedule_does_not_queue_and_changed_plan_is_rejected(store):
    engine, _, _, _, now = store
    with Session(engine) as db:
        identifier = schedule_research(db, plan(), 'operator', 'test', now, now)
        row = db.get(LearningSchedule, identifier)
        row.enabled = False
        db.commit()
        assert queue_due(db, now + timedelta(days=10)) == []
        row.enabled = True
        row.plan = row.plan | {'interval_days': 8}
        db.commit()
        with pytest.raises(ValueError, match='changed'):
            queue_due(db, now + timedelta(days=10))


def test_future_job_cannot_inspect_future_data(store):
    engine, _, _, settings, now = store
    settings = settings.model_copy(update={'demo_mode': False})
    with Session(engine) as db:
        identifier = schedule_research(db, plan(), 'operator', 'test', now + timedelta(days=7), now)
        run_id = digest([identifier, 'future-test'])
        db.add(LearningRun(id=run_id, schedule_id=identifier, scheduled_for=now + timedelta(days=7), state='QUEUED', result={}))
        db.commit()
        report = run_research(db, run_id, 'test', settings, now)
        assert 'not due' in report['reason']
        assert db.get(LearningRun, run_id).state == 'FAILED'


@pytest.mark.parametrize('lose_lease', [False, True])
def test_research_job_registers_only_experimental_and_fences_stale_workers(store, monkeypatch, lose_lease):
    from app.market_data.fixtures import demo_candles
    from app.models.tables import PaperDeploymentSlot

    engine, _, _, settings, now = store
    settings = settings.model_copy(update={'demo_mode': False})
    rows = demo_candles(count=100)
    calls = []

    async def ingest_stub(*args):
        return 0

    def train_stub(*args, **kwargs):
        assert kwargs['validation_only'] is True
        calls.append('fit')
        if lose_lease:
            with Session(engine) as other:
                job = other.get(LearningRun, run_id)
                job.state = 'UNKNOWN'
                other.commit()
        return {'version': 'TEST-ONLY-scheduled', 'validation': {'multiclass_brier': .6},
                'partitions': {'validation': ['test-start', 'test-end']}, 'sample_counts': {}, 'walk_forward': []}

    def replay_stub(*args):
        assert args[4] == 'validation'
        calls.append('replay')
        return {'metrics': {'trades': 0}}

    monkeypatch.setattr('app.machine_learning.learning.load_candles', lambda *a, **k: rows)
    monkeypatch.setattr('app.machine_learning.learning.ingest', ingest_stub)
    monkeypatch.setattr('app.machine_learning.learning.coverage_report', lambda *a, **k: {'research_ready': True, 'input_candles': {}})
    monkeypatch.setattr('app.machine_learning.learning.train_candidates', train_stub)
    monkeypatch.setattr('app.machine_learning.learning.evaluate_registered', replay_stub)
    with Session(engine) as db:
        schedule_research(db, plan(), 'operator', 'mock positive pipeline', now, now)
        run_id = queue_due(db, now)[0]
        result = run_research(db, run_id, 'worker', settings, now)
        assert result['execution_authority'] is False
        assert db.scalar(select(func.count()).select_from(PaperDeploymentSlot)) == 0
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0
        if lose_lease:
            assert result['status'] == 'LEASE_LOST'
            assert db.get(LearningRun, run_id).state == 'UNKNOWN'
            assert db.get(ModelVersion, 'TEST-ONLY-scheduled') is None
        else:
            assert db.get(LearningRun, run_id).state == 'COMPLETED'
            assert calls == ['fit', 'replay', 'replay']
            assert db.get(ModelVersion, 'TEST-ONLY-scheduled').status == 'EXPERIMENTAL'
            assert result['final_test'] == 'PROSPECTIVE_UNTOUCHED_PERIOD_REQUIRED'


def test_outcome_attribution_is_exact_and_idempotent(deployment_store):
    engine, candidate, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        deployment = test_deployment.deploy(db, settings, now, reviews)
        payload = candidate.model_dump(mode='json') | {'model_version': 'TEST-ONLY-first', 'deployment_id': deployment,
                    'probability': '.8', 'probability_stop': '.1', 'probability_timeout': '.1', 'source': 'oanda'}
        db.add(SignalRow(id='outcome-test', symbol=candidate.symbol, strategy=candidate.strategy,
                         time=now, status='APPROVED', payload=payload, reasons=[]))
        db.flush()
        db.add(OrderRow(id='outcome-test', signal_id='outcome-test', mode='PAPER', state='CLOSED',
                        symbol=candidate.symbol, direction='LONG', units=1, entry=candidate.entry, stop=candidate.stop,
                        target=candidate.target, opened_at=now, closed_at=now+timedelta(minutes=5),
                        expires_at=now+timedelta(hours=1), pnl=1, exit=candidate.target,
                        planned_risk=1, close_reason='TAKE_PROFIT', fees_paid=0, financing_bars=0,
                        execution={'schema': 'paper-cost-v1', 'source': 'oanda', 'timeframe': 300,
                                   'fee_rate': '0', 'slippage': '.00001', 'financing_per_bar': '0',
                                   'deployment_id': deployment, 'account_equity_at_entry': '10000'}))
        db.commit()
        assert collect_outcomes(db) == 1 and collect_outcomes(db) == 0
        outcome = db.scalar(select(TradeOutcome))
        assert outcome.model_id == 'TEST-ONLY-first' and outcome.status == 'VERIFIED_PAPER'
        assert outcome.detail['probabilities']['target'] == '.8'
        assert outcome.detail['outcome_label'] == 1 and not outcome.detail['training_eligible']
        report = monitor_model(db, outcome.model_id)
        assert report['status'] == 'INSUFFICIENT_DATA' and report['closed_trades'] == 1


def test_monitor_small_samples_and_checksum_drift_are_not_hidden(store):
    engine, candidate, _, _, now = store
    with Session(engine) as db:
        report = monitor_model(db, candidate.model_version)
        assert report['status'] == 'INSUFFICIENT_DATA' and report['win_rate'] is None
        detail = {'currency': 'USD', 'net_pnl': '-1', 'opened_at': now.isoformat(), 'closed_at': now.isoformat(),
                  'outcome_label': 0, 'probabilities': {'stop': '.1', 'target': '.8', 'timeout': '.1'}, 'net_r': '-1'}
        db.add(TradeOutcome(id='corrupt', mode='PAPER', order_id='test-only', model_id=candidate.model_version,
                            closed_at=now, status='VERIFIED_PAPER', detail=detail, detail_sha256='wrong'))
        db.commit()
        with pytest.raises(ValueError, match='checksum'):
            monitor_model(db, candidate.model_version)


def test_uncertainty_and_distribution_diagnostics():
    lo, hi = wilson(1, 2)
    assert lo < .1 and hi > .9
    assert wilson(0, 0) is None
    assert psi([10]*10, [10]*10) == pytest.approx(0)
    assert psi([10]*10, [100]+[0]*9) > .2
    policy = drift_policy()
    assert policy['minimum_independent_outcomes_per_window'] == 200
    assert policy['sha256'] == digest({k:v for k,v in policy.items() if k != 'sha256'})


def test_final_test_is_not_scored_by_validation_only_training(tmp_path, monkeypatch):
    from decimal import Decimal as D

    from sklearn.calibration import CalibratedClassifierCV

    from app.backtesting.simulator import FillAssumptions
    from app.machine_learning.candidate_training import dataset, purged_partitions, train_candidates
    from app.machine_learning.registry import ModelUnavailable, load_verified
    from app.market_data.fixtures import demo_candles

    rows = demo_candles(count=2000)
    costs = FillAssumptions(D('.00002'), D('.00001'))
    samples, _ = dataset(rows, D('.00001'), 'trend', costs)
    test_first = purged_partitions(samples)[-1][0]
    calls = []
    original = CalibratedClassifierCV.predict_proba

    def capture(self, values):
        calls.append(int(values.index.max()))
        return original(self, values)

    monkeypatch.setattr(CalibratedClassifierCV, 'predict_proba', capture)
    report = train_candidates(rows, D('.00001'), 'trend', costs, tmp_path, validation_only=True)
    assert calls and max(calls) < test_first
    assert report['test'] is None and report['test_economics'] is None
    assert 'test' not in report['class_frequency_baseline']
    assert report['evaluation_mode'] == 'VALIDATION_ONLY'
    for fold in report['walk_forward']:
        if fold['status'] == 'EVALUATED':
            assert fold['training_label_end'] < fold['calibration_start']
            assert fold['calibration_label_end'] < fold['validation_start']
            assert fold['validation_end'] < report['partitions']['test'][0]
    version = ModelVersion(id=report['version'], metadata_json=report, status='EXPERIMENTAL')
    assert load_verified(version, tmp_path) is not None
    monkeypatch.setattr('app.machine_learning.registry.research_code_contract', lambda: {'changed': True})
    with pytest.raises(ModelUnavailable, match='implementation changed'):
        load_verified(version, tmp_path)


def test_repeated_deterioration_requires_approved_policy_and_current_model(deployment_store):
    from app.machine_learning.monitoring import approve_drift_policy, enforce_monitor

    engine, _, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        test_deployment.deploy(db, settings, now, reviews)
        for i in range(400):
            opened = now - timedelta(hours=1000-i*2)
            closed = opened + timedelta(hours=1)
            detail = {'currency': 'USD', 'net_pnl': '-1', 'opened_at': opened.isoformat(),
                      'closed_at': closed.isoformat(), 'outcome_label': 0,
                      'probabilities': {'stop': '.1', 'target': '.8', 'timeout': '.1'}, 'net_r': '-1'}
            db.add(TradeOutcome(id=f'outcome-{i}', mode='PAPER', order_id=f'test-{i}', model_id='TEST-ONLY-first',
                                closed_at=closed, status='VERIFIED_PAPER', detail=detail, detail_sha256=digest(detail)))
        db.commit()
        report = monitor_model(db, 'TEST-ONLY-first')
        assert report['status'] == 'DETERIORATION_DETECTED'
        assert not enforce_monitor(db, report, settings)
        enabled = settings.model_copy(update={'enable_drift_suspension': True})
        assert not enforce_monitor(db, report, enabled)
        approve_drift_policy(db, 'test-operator', 'Explicit synthetic-monitor test approval', now)
        assert enforce_monitor(db, report, enabled)
        assert db.get(Account, 'PAPER').suspended
        assert db.get(ModelVersion, 'TEST-ONLY-first').status == 'EXPERIMENTAL'


def test_forged_deterioration_report_cannot_suspend(deployment_store):
    engine, _, _, settings, now, reviews = deployment_store
    with Session(engine) as db:
        test_deployment.deploy(db, settings, now, reviews)
        approve_drift_policy(db, 'operator', 'test', now)
        report = monitor_model(db, 'TEST-ONLY-first')
        report['status'] = 'DETERIORATION_DETECTED'
        assert not enforce_monitor(db, report, settings.model_copy(update={'enable_drift_suspension': True}))
        assert not db.get(Account, 'PAPER').suspended
