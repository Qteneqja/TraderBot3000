"""Comparison orchestration with explicitly mocked artifact verification/portfolio replay."""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.backtesting.comparison import compare_incumbent
from app.backtesting.simulator import FillAssumptions
from app.core.config import Settings
from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.market_data.fingerprint import candle_manifest
from app.market_data.fixtures import demo_candles
from app.models.tables import ModelVersion


def test_common_period_checks_cutoff_and_sealed_test_and_preserves_input_context(monkeypatch):
    engine = make_engine('sqlite://')
    Base.metadata.create_all(engine)
    rows = demo_candles(count=500)
    metadata = {'symbol': 'EUR_USD', 'source': 'fixture', 'timeframe': 300, 'strategy': 'trend', 'horizon': 12,
                'training_cutoff': rows[60].time.isoformat(), 'input_candles': candle_manifest(rows),
                'evaluation_mode': 'FULL', 'partitions': {'validation': [rows[70].time.isoformat(), rows[100].time.isoformat()],
                                                       'test': [rows[150].time.isoformat(), rows[200].time.isoformat()]}}
    monkeypatch.setattr('app.backtesting.comparison.load_verified', lambda *a: object())
    monkeypatch.setattr('app.backtesting.comparison.load_candles', lambda *a, **k: rows)
    calls = []

    def replay(candles, *args, **kwargs):
        calls.append((candles, kwargs))
        return {'metrics': {'trades': 0}}

    monkeypatch.setattr('app.backtesting.comparison.run_portfolio', replay)
    with Session(engine) as db:
        bootstrap(db)
        row = ModelVersion(id='mock-incumbent', status='EXPERIMENTAL', metadata_json=metadata)
        db.add(row)
        db.commit()
        settings = Settings(_env_file=None)
        costs = FillAssumptions(Decimal('.0002'), Decimal('.00001'))
        report = compare_incumbent(db, row.id, metadata, costs, settings)
        assert report['qualification_evidence'] is False and report['execution_authority'] is False
        assert calls[0][0][0] == rows[0] and calls[0][0][-1] == rows[112]
        row.metadata_json = metadata | {'training_cutoff': rows[70].time.isoformat()}
        with pytest.raises(ValueError, match='overlaps'):
            compare_incumbent(db, row.id, metadata, costs, settings)
        row.metadata_json = metadata | {'evaluation_mode': 'VALIDATION_ONLY', 'partitions': {'test': [rows[90].time.isoformat(), rows[200].time.isoformat()]}}
        with pytest.raises(ValueError, match='sealed'):
            compare_incumbent(db, row.id, metadata, costs, settings)
        assert len(calls) == 1
