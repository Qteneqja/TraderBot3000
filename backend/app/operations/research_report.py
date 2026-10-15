"""Reproducible validation-only campaign report; never opens final partitions."""

from sqlalchemy import select

from app.machine_learning.assessment import partition_checks
from app.machine_learning.contracts import research_code_contract
from app.machine_learning.policy import acceptance_policy
from app.models.tables import Event, LearningRun, LearningSchedule, ModelVersion


def campaign_report(db, campaign, now, settings):
    declaration = next((row for row in db.scalars(select(Event).where(
        Event.kind == 'activation_research_predeclared').order_by(Event.time.desc())).all()
        if row.detail.get('campaign') == campaign), None)
    if declaration is None:
        raise ValueError('Unknown predeclared campaign')
    identifiers = declaration.detail['schedules']
    policy, code = acceptance_policy(settings), research_code_contract()
    batches = []
    for run, schedule in db.execute(select(LearningRun, LearningSchedule).join(LearningSchedule)
            .where(LearningRun.schedule_id.in_(identifiers)).order_by(LearningRun.scheduled_for, LearningRun.id)):
        candidates = []
        for result in run.result.get('candidates', []):
            item = {key: result.get(key) for key in ('model', 'family', 'status', 'error_type', 'reason')}
            version = db.get(ModelVersion, result.get('model')) if result.get('model') else None
            if version is not None:
                metadata = version.metadata_json
                item.update({key: metadata.get(key) for key in ('artifact_sha256', 'dataset_sha256',
                    'input_candles', 'partitions', 'sample_counts', 'coverage', 'validation',
                    'validation_economics', 'prediction_reference_validation_only', 'excluded', 'walk_forward')})
                item['class_frequency_baseline'] = metadata['class_frequency_baseline'].get('validation')
                item['strategy_code_matches_current'] = metadata.get('research_code') == code
                item['policy_matches_current'] = metadata.get('acceptance_policy') == policy
                if result.get('portfolio') and result.get('stressed_portfolio'):
                    evidence = partition_checks(result['portfolio'], result['stressed_portfolio'],
                        metadata['validation'], item['class_frequency_baseline'], policy)
                    item['validation_screen'] = evidence
                    item['failed_validation_checks'] = [k for k, v in evidence['checks'].items() if not v]
                    item['rejection_reasons'] = result['portfolio'].get('rejections', {})
                item['final_test'] = 'NOT_EVALUATED'
                item['deployment_eligible'] = False
            candidates.append(item)
        batches.append({'run': run.id, 'symbol': schedule.plan['symbol'], 'strategy': schedule.plan['strategy'],
                        'state': run.state, 'plan': schedule.plan, 'candidates': candidates})
    return {'schema': 'activation-research-report-v1', 'campaign': campaign, 'as_of': now.isoformat(),
            'predeclared_at': declaration.time.isoformat(), 'policy': policy,
            'current_code_sha256': code['sha256'], 'declared_code_sha256': declaration.detail['code_sha256'],
            'planned_fits': declaration.detail['planned_fits'], 'batches': batches,
            'final_test': 'NOT_EVALUATED', 'execution_authority': False,
            'note': 'Validation screens are diagnostic; independent future qualification and explicit activation remain mandatory.'}
