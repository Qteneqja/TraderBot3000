"""Explicit, one-shot future evaluation of a frozen candidate. No refitting or promotion."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
from sqlalchemy import select, update

from app.backtesting.registered import evaluate_registered
from app.backtesting.simulator import FillAssumptions
from app.execution.paper import lock_account
from app.machine_learning.assessment import assess_model, partition_checks
from app.machine_learning.candidate_training import (
    CANDIDATE_FEATURES,
    dataset,
    economic_report,
    purged_partitions,
)
from app.machine_learning.policy import acceptance_policy, digest
from app.machine_learning.registry import load_verified
from app.machine_learning.training import scores
from app.market_data.coverage import coverage_report
from app.market_data.fingerprint import candle_manifest, verified_training_rows
from app.market_data.store import load_candles
from app.models.tables import Event, FinalEvaluation, Instrument, ModelVersion


def implementation_hash():
    source = Path(__file__)
    files = (source, source.with_name('assessment.py'), source.with_name('training.py'),
             source.parents[2] / 'requirements.lock')
    return digest({file.name: hashlib.sha256(file.read_text(encoding='utf-8').encode()).hexdigest() for file in files})


def training_end(db, symbol, source, start, end):
    """Exclude every reserved future test, including outcomes after its last entry."""
    for row in db.scalars(select(FinalEvaluation)).all():
        plan = row.plan
        if row.id != digest(plan):
            raise ValueError("Prospective evaluation plan changed")
        if row.state in ('RESERVED', 'EVALUATING') and (plan["symbol"], plan["source"]) == (symbol, source):
            first = datetime.fromisoformat(plan["start"])
            last = datetime.fromisoformat(plan["end"]) + timedelta(seconds=plan["timeframe"] * plan["horizon"])
            if start < last and end > first:
                end = min(end, first)
    if end <= start:
        raise ValueError("Training window intersects a reserved prospective holdout")
    return end


def holdout_provenance(db, version, allow_evaluating=False):
    """A reserved period can only qualify through its exact frozen finalization receipt."""
    metadata = version.metadata_json
    manifest = metadata.get('input_candles', {})
    if not manifest:
        return True  # Other provenance gates reject absent manifests.
    try:
        first, last = [datetime.fromisoformat(manifest[key]) for key in ('start', 'end')]
        test_first, test_last = [datetime.fromisoformat(t) for t in metadata.get('partitions', {}).get(
            'test', [manifest['start'], manifest['end']])]
        test_last += timedelta(seconds=metadata.get('timeframe', 0) * metadata.get('horizon', 0))
        for row in db.scalars(select(FinalEvaluation)).all():
            plan = row.plan
            if row.id != digest(plan):
                return False
            if (plan['symbol'], plan['source']) != (metadata.get('symbol'), metadata.get('source')):
                continue
            start, end = [datetime.fromisoformat(plan[key]) for key in ('start', 'end')]
            end += timedelta(seconds=plan['timeframe'] * plan['horizon'])
            active_overlap = row.state in ('RESERVED', 'EVALUATING') and first < end and last >= start
            if active_overlap or (test_first < end and test_last >= start):
                receipt = metadata.get('prospective_final', {})
                states = ('EVALUATING', 'COMPLETED') if allow_evaluating else ('COMPLETED',)
                if (row.model_id != version.id or row.state not in states
                    or receipt.get('reservation') != row.id or receipt.get('plan') != plan
                    or receipt.get('refitted') is not False
                    or version.id != 'final-' + row.id[:48]):
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def validation_evidence(db, version, root, settings):
    metadata = version.metadata_json
    policy = acceptance_policy(settings)
    if (settings.demo_mode or settings.trading_mode != "PAPER" or version.status != "EXPERIMENTAL"
        or metadata.get("evaluation_mode") != "VALIDATION_ONLY"
        or metadata.get("source") not in ("oanda", "coinbase")
        or metadata.get("acceptance_policy") != policy
        or not metadata.get("coverage", {}).get("research_ready")
        or settings.initial_probability_threshold < Decimal('.8') or settings.min_risk_reward < 2
        or metadata.get("sample_counts", {}).get("calibration", 0) < policy["minimum_calibration_samples"]
        or len(metadata.get("walk_forward", [])) != policy["walk_forward_folds"]
        or any(f.get("status") != "EVALUATED" for f in metadata.get("walk_forward", []))):
        raise ValueError("Frozen provider candidate lacks current validation prerequisites")
    load_verified(version, root)
    base = evaluate_registered(db, version.id, root, settings, "validation")
    stress = evaluate_registered(db, version.id, root, settings, "validation", Decimal(policy["cost_stress_multiplier"]))
    checks = partition_checks(base, stress, metadata["validation"], metadata["class_frequency_baseline"]["validation"], policy)
    failed = [key for key, value in checks["checks"].items() if not value]
    if failed:
        raise ValueError("Validation gates failed: " + ", ".join(failed))
    rows = load_candles(db, metadata["symbol"], metadata["timeframe"], metadata["source"], 1_000_000)
    rows = verified_training_rows(rows, metadata["input_candles"])
    samples, _ = dataset(rows, Decimal(metadata["tick"]), metadata["strategy"],
                         FillAssumptions(**{k: Decimal(v) for k, v in metadata["costs"].items()}), metadata["horizon"])
    train = purged_partitions(samples)[0]
    if len(train) != metadata["sample_counts"]["train"]:
        raise ValueError("Original training samples cannot be reproduced")
    frequency = np.bincount(samples.iloc[train].label.to_numpy(dtype=int), minlength=3) / len(train)
    return {"validation": checks, "training_class_frequency": frequency.tolist()}


def reserve_period(db, parent_id, root, settings, start, end, operator, reason, now=None):
    now = now or datetime.now(timezone.utc)
    if not operator.strip() or not reason.strip():
        raise ValueError("Explicit operator attribution required")
    if any(t.tzinfo is None for t in (start, end, now)) or start <= now or end-start < timedelta(days=45):
        raise ValueError("Reserve an aware, strictly future period of at least 45 days")
    parent = db.get(ModelVersion, parent_id)
    if parent is None:
        raise ValueError("Unknown parent model")
    metadata = parent.metadata_json
    timeframe = metadata["timeframe"]
    if timeframe not in (60, 300, 900, 3600):
        raise ValueError('Unsupported final evaluation timeframe')
    if start.timestamp() % timeframe or end.timestamp() % timeframe:
        raise ValueError("Evaluation boundaries must align to the candle timeframe")
    evidence = validation_evidence(db, parent, root, settings)
    parent_hash = digest(metadata)
    db.rollback()
    try:
        lock_account(db)  # Serializes reservations without changing account risk or execution state.
        parent = db.get(ModelVersion, parent_id, populate_existing=True)
        if digest(parent.metadata_json) != parent_hash:
            raise ValueError("Parent evidence changed during reservation")
        if db.scalar(select(FinalEvaluation.id).where(FinalEvaluation.parent_id == parent_id)):
            raise ValueError("Parent already has a final evaluation; periods cannot be moved or retried")
        context_start = start - timedelta(seconds=60*timeframe)
        embargo_end = end + timedelta(seconds=timeframe*metadata['horizon'])
        for previous in db.scalars(select(FinalEvaluation)).all():
            plan = previous.plan
            if previous.id != digest(plan):
                raise ValueError("Existing final evaluation plan changed")
            if (plan['symbol'], plan['source']) == (metadata['symbol'], metadata['source']):
                first = datetime.fromisoformat(plan['start']) - timedelta(seconds=60*plan['timeframe'])
                last = datetime.fromisoformat(plan['end']) + timedelta(seconds=plan['timeframe']*plan['horizon'])
                if context_start < last and embargo_end > first:
                    raise ValueError("Final test context/outcome periods may not overlap across models")
        plan = {"schema": "prospective-final-v1", "parent": parent_id, "parent_metadata_sha256": parent_hash,
                "symbol": metadata['symbol'], "source": metadata['source'], "timeframe": timeframe,
                "horizon": metadata['horizon'], "start": start.isoformat(), "end": end.isoformat(),
                "reserved_at": now.isoformat(), "operator": operator[:120], "reason": reason[:512],
                "policy": acceptance_policy(settings), "implementation_sha256": implementation_hash(),
                "selection_evidence": evidence, "execution_authority": False}
        identifier = digest(plan)
        db.add(FinalEvaluation(id=identifier, parent_id=parent_id, state="RESERVED", created_at=now, plan=plan, result={}))
        db.add(Event(kind="final_evaluation_reserved", detail={"evaluation": identifier, "parent": parent_id,
                                                             "operator": operator[:120], "execution_authority": False}))
        db.commit()
        return identifier
    except Exception:
        db.rollback()
        raise


def abandon_period(db, identifier, operator, reason):
    if not operator.strip() or not reason.strip():
        raise ValueError('Operator and reason required for permanent abandonment')
    try:
        row = db.scalar(select(FinalEvaluation).where(FinalEvaluation.id == identifier).with_for_update()
                        .execution_options(populate_existing=True))
        if row is None or row.state not in ('RESERVED', 'EVALUATING') or row.id != digest(row.plan):
            raise ValueError('Only an intact pending evaluation may be abandoned')
        row.state = 'ABANDONED'
        row.result = {'operator': operator[:120], 'reason': reason[:512], 'automatic_retry': False,
                      'execution_authority': False}
        db.add(Event(kind='final_evaluation_abandoned', detail={'evaluation': identifier,
            'operator': operator[:120], 'reason': reason[:512], 'period_reusable_as_final_test': False}))
        db.commit()
    except Exception:
        db.rollback()
        raise


def evaluating_row(db, identifier):
    row = db.scalar(select(FinalEvaluation).where(FinalEvaluation.id == identifier).with_for_update()
                    .execution_options(populate_existing=True))
    if row is None or row.state != 'EVALUATING':
        raise ValueError('Evaluation claim no longer active; results require operator review')
    return row


def evaluate_period(db, identifier, root, settings, now=None):
    now = now or datetime.now(timezone.utc)
    row = db.get(FinalEvaluation, identifier)
    if row is None or row.id != digest(row.plan):
        raise ValueError("Unknown or changed evaluation plan")
    plan = dict(row.plan)
    end = datetime.fromisoformat(plan['end'])
    completed_end = end + timedelta(seconds=plan['horizon'] * plan['timeframe'])
    if (settings.demo_mode or settings.trading_mode != 'PAPER' or now.tzinfo is None or now < completed_end
        or plan['policy'] != acceptance_policy(settings) or plan['implementation_sha256'] != implementation_hash()):
        raise ValueError("Future outcomes incomplete or evaluation implementation/policy changed")
    claimed = db.execute(update(FinalEvaluation).where(FinalEvaluation.id == identifier,
        FinalEvaluation.state == 'RESERVED').values(state='EVALUATING').returning(FinalEvaluation.id)).scalar_one_or_none()
    db.commit()  # Durable one-shot claim BEFORE loading any held-out outcomes.
    if claimed is None:
        raise ValueError("Evaluation already claimed; no automatic final-test retry")
    try:
        parent = db.get(ModelVersion, plan['parent'], populate_existing=True)
        if digest(parent.metadata_json) != plan['parent_metadata_sha256']:
            raise ValueError("Frozen parent metadata changed")
        model = load_verified(parent, root)
        metadata = dict(parent.metadata_json)
        start = datetime.fromisoformat(plan['start'])
        input_start = datetime.fromisoformat(metadata['input_candles']['start'])
        rows = load_candles(db, plan['symbol'], plan['timeframe'], plan['source'], 1_000_000,
                            start=input_start, end=completed_end)
        verified_training_rows(rows, metadata['input_candles'])
        coverage = coverage_report(rows, input_start, completed_end, now, oanda_division=settings.oanda_division)
        if not coverage['research_ready']:
            raise ValueError("Final provider data coverage failed")
        # Require the FUTURE slice itself to pass, not only the much larger prior history.
        future = [c for c in rows if start <= c.time < end]
        future_coverage = coverage_report(future, start, end, now, minimum_days=0,
                                          oanda_division=settings.oanda_division)
        if not future_coverage['research_ready']:
            raise ValueError("Future evaluation session completeness failed")
        instrument = db.get(Instrument, plan['symbol'])
        costs = FillAssumptions(**{k: Decimal(v) for k, v in metadata['costs'].items()})
        samples, _ = dataset(rows, instrument.tick_size, metadata['strategy'], costs, plan['horizon'])
        samples = samples[(samples.time >= start) & (samples.time < end)]
        if len(samples) < 100:
            raise ValueError("Insufficient future final candidates")
        probabilities = np.asarray(model.predict_proba(samples[CANDIDATE_FEATURES]))
        if (probabilities.shape != (len(samples), 3) or not np.isfinite(probabilities).all()
            or (probabilities < 0).any() or (probabilities > 1).any()
            or not np.allclose(probabilities.sum(axis=1), 1)):
            raise ValueError("Invalid frozen-model probability output")
        labels = samples.label.to_numpy(dtype=int)
        version_id = 'final-' + identifier[:48]
        report = {k: v for k, v in metadata.items() if k not in ('artifact_sha256', 'artifact_filename')}
        report.update(version=version_id, evaluation_mode='FULL', status='EXPERIMENTAL',
            input_candles=candle_manifest(rows), coverage=coverage,
            dataset_sha256=digest([metadata['dataset_sha256'], identifier, candle_manifest(rows)]),
            partitions=metadata['partitions'] | {'test': [str(samples.time.min()), str(samples.time.max())]},
            sample_counts=metadata['sample_counts'] | {'test': len(samples)},
            class_frequency_baseline=metadata['class_frequency_baseline'] | {'test': scores(labels,
                np.tile(plan['selection_evidence']['training_class_frequency'], (len(samples), 1)))},
            test=scores(labels, probabilities), test_economics=economic_report(samples, probabilities),
            prospective_final={'reservation': identifier, 'plan': plan, 'future_coverage': future_coverage,
                               'frozen_parent_artifact_sha256': metadata['artifact_sha256'], 'refitted': False})
        row = evaluating_row(db, identifier)
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        artifact = root / f'{version_id}.joblib'
        # Open exclusively: crashes may leave an orphan artifact requiring operator review.
        with artifact.open('xb') as file:
            joblib.dump({'model': model, 'report': report}, file)
        report = report | {'artifact_filename': artifact.name,
                           'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
        with (root / f'{version_id}.json').open('x', encoding='utf-8') as file:
            json.dump(report, file, indent=2)
        db.add(ModelVersion(id=version_id, status='EXPERIMENTAL', metadata_json=report))
        db.flush()  # Persist the referenced model before updating the reservation FK on PostgreSQL.
        row.model_id = version_id
        db.commit()
        assessment = assess_model(db, version_id, root, settings)
        row = evaluating_row(db, identifier)
        row.state, row.model_id = 'COMPLETED', version_id
        row.result = {'model': version_id, 'review': assessment['review_id'], 'status': assessment['status'],
                      'reasons': assessment['reasons'], 'refitted': False, 'execution_authority': False}
        db.add(Event(kind='final_evaluation_completed', detail={'evaluation': identifier, 'model': version_id,
                                                              'promoted': False}))
        db.commit()
        return row.result
    except Exception as exc:
        db.rollback()
        db.execute(update(FinalEvaluation).where(FinalEvaluation.id == identifier,
            FinalEvaluation.state == 'EVALUATING').values(state='FAILED', result={
                'error_type': type(exc).__name__, 'automatic_retry': False, 'execution_authority': False}))
        db.add(Event(kind='final_evaluation_failed', detail={'evaluation': identifier, 'error_type': type(exc).__name__}))
        db.commit()
        raise
