from datetime import timedelta
from decimal import Decimal as D

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_risk import setup_risk

from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.execution.paper import monitor, reconcile, submit
from app.market_data.store import save_quote
from app.models.tables import Account, ModelVersion, OrderRow

pytestmark = pytest.mark.usefixtures("execution_model_stub")


def seed_test_model(db, candidate):
    db.add(
        ModelVersion(
            id=candidate.model_version,
            status="ACTIVE",
            metadata_json={
                "execution_validated": True,
                **{key: getattr(candidate, key) for key in ("symbol", "strategy", "timeframe", "source")},
            },
        )
    )
    db.commit()


def test_paper_lifecycle_and_duplicate_delivery():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s, q, _, _, settings, now = setup_risk()
    with Session(engine) as db:
        bootstrap(db)
        db.add(
            ModelVersion(
                id=s.model_version,
                status="ACTIVE",
                metadata_json={
                    "execution_validated": True,
                    "symbol": s.symbol,
                    "strategy": s.strategy,
                    "timeframe": s.timeframe,
                    "source": s.source,
                },
            )
        )
        db.commit()
        assert submit(db, s, q, settings, now) == "REJECTED"  # startup reconciliation mandatory
        assert reconcile(db, now)
        s = s.model_copy(update={"id": "second-signal"})
        assert submit(db, s, q, settings, now) == "FILLED"
        assert submit(db, s, q, settings, now) == "FILLED"
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 1
        db.rollback()
        exit_quote = q.model_copy(
            update={"time": now + timedelta(seconds=1), "bid": D("1.126"), "ask": D("1.1261")}
        )
        save_quote(db, exit_quote, exit_quote.time)
        monitor(db, settings, exit_quote.time)
        order = db.get(OrderRow, s.id)
        assert order.state == "CLOSED" and order.pnl > 0 and order.units > 0
        db.rollback()
        monitor(db, settings, exit_quote.time)
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 1


def test_unregistered_model_never_executes():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    s, q, _, _, settings, now = setup_risk()
    with Session(engine) as db:
        bootstrap(db)
        reconcile(db, now)
        assert submit(db, s, q, settings, now) == "REJECTED"
        assert db.scalar(select(func.count()).select_from(OrderRow)) == 0


def test_paper_fees_and_quote_identity_survive_restart(tmp_path):
    from app.execution.paper import money

    engine = make_engine(f"sqlite:///{tmp_path}/restart.db")
    Base.metadata.create_all(engine)
    candidate, quote, _, _, settings, now = setup_risk()
    settings = settings.model_copy(
        update={
            "paper_fee_rate": D(".001"),
            "paper_slippage_ticks": 2,
            "paper_financing_per_unit_per_bar": D(".00001"),
        }
    )
    with Session(engine) as db:
        bootstrap(db)
        seed_test_model(db, candidate)
        reconcile(db, now)
        assert submit(db, candidate, quote, settings, now) == "FILLED"
        order = db.get(OrderRow, candidate.id)
        units, entry = order.units, order.entry
        entry_fee = money(units * entry * D(".001"))
        assert order.fees_paid == entry_fee
        assert db.get(Account, "PAPER").balance == D(10000) - entry_fee

    # A different provider's quote cannot close the position, even if its price hits the target.
    when = now + timedelta(seconds=1)
    with Session(engine) as db:
        wrong = quote.model_copy(
            update={"source": "other-provider", "time": when, "bid": D("1.126"), "ask": D("1.1261")}
        )
        save_quote(db, wrong, when)
        monitor(db, settings, when)
        assert db.get(OrderRow, candidate.id).state == "FILLED"
        charged = db.get(OrderRow, candidate.id).fees_paid
        db.rollback()
        monitor(db, settings, when)
        assert db.get(OrderRow, candidate.id).fees_paid == charged
        assert charged == entry_fee + money(units * D(".00001"))

    # New process configuration cannot change a position's persisted execution contract.
    changed_settings = settings.model_copy(update={"paper_fee_rate": D(".1"), "paper_slippage_ticks": 99})
    when += timedelta(seconds=1)
    with Session(engine) as db:
        closing = wrong.model_copy(update={"source": candidate.source, "time": when})
        save_quote(db, closing, when)
        assert reconcile(db, when)
        monitor(db, changed_settings, when)
        order = db.get(OrderRow, candidate.id)
        assert order.state == "CLOSED"
        assert order.fees_paid == charged + money(candidate.target * units * D(".001"))
        balance = db.get(Account, "PAPER").balance
        assert balance == D(10000) + order.pnl
        db.rollback()
        monitor(db, changed_settings, when)
        assert db.get(Account, "PAPER").balance == balance


def test_unknown_legacy_cost_contract_quarantines_open_position():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    candidate, quote, _, _, settings, now = setup_risk()
    with Session(engine) as db:
        bootstrap(db)
        seed_test_model(db, candidate)
        reconcile(db, now)
        assert submit(db, candidate, quote, settings, now) == "FILLED"
        order = db.get(OrderRow, candidate.id)
        order.execution = {}
        db.commit()
        assert not reconcile(db, now)
        account = db.get(Account, "PAPER")
        assert account.suspended and not account.reconciled
