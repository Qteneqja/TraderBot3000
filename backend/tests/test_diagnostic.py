from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.models.tables import Event, SignalRow
from app.operations.diagnostic import activation_report
from app.operations.research_report import campaign_report


def test_diagnostic_is_bounded_and_does_not_expose_signal_payload_or_event_details(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/diagnostic.db')
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        bootstrap(db)
        db.add(Event(kind='trading_worker_heartbeat', time=now,
                     detail={'secret': 'MUST-NOT-APPEAR', 'evaluations': {'instruments': 4}}))
        for i in range(501):
            db.add(SignalRow(id=str(i), time=now-timedelta(seconds=i), symbol='EUR_USD', strategy='trend',
                status='REJECTED', payload={'secret': 'MUST-NOT-APPEAR', 'source': 'oanda' if i == 0 else 'fixture'},
                reasons=['NO_VALIDATED_CALIBRATED_MODEL'] if i < 500 else ['OLDER_REASON']))
        db.commit()
        report = activation_report(db, Settings(_env_file=None), now)
        assert report['signals']['sample_count'] == 500
        assert report['signals']['stored_counts'] == {'REJECTED': 501}
        assert report['signals']['rejection_reasons'] == {'NO_VALIDATED_CALIBRATED_MODEL': 500}
        assert report['signals']['provider_sample_count'] == 1
        assert report['signals']['provider_rejection_reasons'] == {'NO_VALIDATED_CALIBRATED_MODEL': 1}
        assert report['workers']['trading']['state'] == 'FRESH'
        assert 'MUST-NOT-APPEAR' not in str(report)
        assert activation_report(db, Settings(_env_file=None), now+timedelta(minutes=4))['workers'][
            'trading']['state'] == 'STALE_OR_UNSEEN'


def test_campaign_report_preserves_pending_and_failed_results_without_final_scores(tmp_path):
    from app.models.tables import LearningRun, LearningSchedule

    engine = make_engine(f'sqlite:///{tmp_path}/campaign.db')
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(LearningSchedule(id='schedule', enabled=True, operator='test', reason='test',
            plan={'symbol': 'EUR_USD', 'strategy': 'trend'}, next_due=now))
        db.add(Event(kind='activation_research_predeclared', detail={'campaign': 'test-only',
            'schedules': ['schedule'], 'code_sha256': 'test-code', 'planned_fits': 1}))
        db.commit()
        db.add(LearningRun(id='run', schedule_id='schedule', scheduled_for=now, state='QUEUED', result={}))
        db.commit()
        report = campaign_report(db, 'test-only', now, Settings(_env_file=None))
        assert report['batches'][0]['state'] == 'QUEUED'
        assert report['batches'][0]['candidates'] == []
        row = db.get(LearningRun, 'run')
        row.state = 'FAILED'
        row.result = {'candidates': [{'family': 'logistic', 'status': 'FAILED', 'reason': 'Insufficient samples'}]}
        db.commit()
        report = campaign_report(db, 'test-only', now, Settings(_env_file=None))
        assert report['final_test'] == 'NOT_EVALUATED' and report['execution_authority'] is False
        assert report['batches'][0]['candidates'][0]['reason'] == 'Insufficient samples'
