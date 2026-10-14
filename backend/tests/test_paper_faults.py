"""Fault injection and accelerated replay; not evidence of a real-time soak or market edge."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from test_execution import seed_test_model
from test_risk import setup_risk

from app.database.bootstrap import bootstrap
from app.database.session import Base, make_engine
from app.execution.paper import money, monitor, reconcile, submit
from app.market_data.store import save_quote
from app.models.tables import Account, OrderEvent, OrderRow, SignalRow

pytestmark = pytest.mark.usefixtures("execution_model_stub")


@pytest.fixture(params=["sqlite", "postgresql"])
def store(request, tmp_path):
    if request.param == "postgresql":
        url = os.environ.get("TEST_POSTGRES_URL")
        if not url:
            pytest.skip("Set TEST_POSTGRES_URL for isolated PostgreSQL concurrency/fault tests")
        admin_engine = create_engine(url)
        schema = "test_paper_" + uuid4().hex
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = admin_engine.execution_options(schema_translate_map={None: schema})
    else:
        engine = make_engine(f"sqlite:///{tmp_path}/faults.db")
    Base.metadata.create_all(engine)
    candidate, quote, _, _, settings, now = setup_risk()
    with Session(engine) as db:
        bootstrap(db)
        seed_test_model(db, candidate)
        save_quote(db, quote, now)
        reconcile(db, now)
    try:
        yield engine, candidate, quote, settings, now
    finally:
        if request.param == "postgresql":
            # This unique schema is owned entirely by this test, never the application's public schema.
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def counts(db):
    return tuple(db.scalar(select(func.count()).select_from(t)) for t in (SignalRow, OrderRow, OrderEvent))


def test_concurrent_duplicate_submission_is_one_durable_order(store):
    engine, candidate, quote, settings, now = store
    barrier = Barrier(6)

    def delivery(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return submit(db, candidate, quote, settings, now)

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert list(pool.map(delivery, range(6))) == ["FILLED"] * 6
    with Session(engine) as db:
        assert counts(db) == (1, 1, 4)


def test_concurrent_distinct_signals_share_account_risk_reservation(store):
    engine, candidate, quote, settings, now = store
    barrier = Barrier(6)

    def delivery(i):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return submit(db, candidate.model_copy(update={"id": f"parallel-{i}"}), quote, settings, now)

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(delivery, range(6)))
    with Session(engine) as db:
        orders = db.scalars(select(OrderRow)).all()
        assert 0 < len(orders) <= settings.max_open_positions
        reserved = sum((o.planned_risk for o in orders), D(0))
        assert reserved <= D(10000) * D(".01")
        assert sum((o.units * o.entry for o in orders), D(0)) <= D(10000)
        assert counts(db)[0] == 6


@pytest.mark.parametrize("durable", [False, True])
def test_crash_before_or_after_commit_does_not_duplicate_or_partially_charge(store, durable):
    engine, candidate, quote, settings, now = store
    settings = settings.model_copy(update={"paper_fee_rate": D(".001")})
    with Session(engine) as db:
        commit = db.commit

        def crash():
            if durable:
                commit()
            raise RuntimeError("Injected process failure at commit boundary")

        db.commit = crash
        with pytest.raises(RuntimeError, match="Injected"):
            submit(db, candidate, quote, settings, now)
    with Session(engine) as db:
        assert counts(db) == ((1, 1, 4) if durable else (0, 0, 0))
        db.rollback()
        assert reconcile(db, now)
        assert submit(db, candidate, quote, settings, now) == "FILLED"
        order = db.get(OrderRow, candidate.id)
        assert counts(db) == (1, 1, 4)
        assert db.get(Account, "PAPER").balance == D(10000) - order.fees_paid


def test_failed_exit_transaction_can_be_replayed_exactly_once(store):
    engine, candidate, quote, settings, now = store
    settings = settings.model_copy(update={"paper_fee_rate": D(".001")})
    with Session(engine) as db:
        submit(db, candidate, quote, settings, now)
        entry_balance = db.get(Account, "PAPER").balance
    closing = quote.model_copy(
        update={"time": now + timedelta(seconds=1), "bid": D("1.126"), "ask": D("1.1261")}
    )
    with Session(engine) as db:
        save_quote(db, closing, closing.time)
        db.commit = lambda: (_ for _ in ()).throw(RuntimeError("Injected exit failure"))
        with pytest.raises(RuntimeError, match="exit failure"):
            monitor(db, settings, closing.time)
    with Session(engine) as db:
        assert db.get(OrderRow, candidate.id).state == "FILLED"
        assert db.get(Account, "PAPER").balance == entry_balance
        db.rollback()
        monitor(db, settings, closing.time)
        balance = db.get(Account, "PAPER").balance
        assert balance == D(10000) + db.get(OrderRow, candidate.id).pnl
        db.rollback()
        assert submit(db, candidate, quote, settings, closing.time) == "CLOSED"
        monitor(db, settings, closing.time)
        assert db.get(Account, "PAPER").balance == balance


def test_daily_rollover_preserves_gap_loss_instead_of_resetting_it(store):
    engine, candidate, quote, settings, _ = store
    now = datetime(2026, 1, 4, 23, 59, 59, tzinfo=timezone.utc)
    candidate = candidate.model_copy(update={"time": now, "expires_at": now + timedelta(minutes=5)})
    quote = quote.model_copy(update={"time": now})
    with Session(engine) as db:
        submit(db, candidate, quote, settings, now)
        old_equity = db.get(Account, "PAPER").equity
    when = now + timedelta(seconds=2)
    with Session(engine) as db:
        # Direct assignment is intentional: this test clock predates the seeded quote.
        from app.models.tables import QuoteRow

        row = db.get(QuoteRow, candidate.symbol)
        row.time, row.bid, row.ask = when, D("1.04"), D("1.0402")
        db.commit()
        monitor(db, settings, when)
        account = db.get(Account, "PAPER")
        assert account.day == "2026-01-05" and account.week == "2026-02"
        assert account.day_start == old_equity and account.week_start == old_equity
        assert (account.day_start - account.equity) / account.day_start >= settings.max_daily_loss


def test_accelerated_restart_replay_reconciles_ledger(store):
    engine, base, quote, settings, now = store
    settings = settings.model_copy(
        update={"paper_fee_rate": D(".0001"), "paper_financing_per_unit_per_bar": D(".00001")}
    )
    for i in range(30):
        when = now + timedelta(hours=3 * i)
        candidate = base.model_copy(
            update={"id": f"soak-{i}", "time": when, "expires_at": when + timedelta(minutes=5)}
        )
        current = quote.model_copy(update={"time": when})
        with Session(engine) as db:
            save_quote(db, current, when)
            assert reconcile(db, when)
            submit(db, candidate, current, settings, when)
        # New sessions emulate restart boundaries; winning test quotes are not performance evidence.
        exit_quote = current.model_copy(
            update={"time": when + timedelta(seconds=301), "bid": D("1.126"), "ask": D("1.1262")}
        )
        with Session(engine) as db:
            save_quote(db, exit_quote, exit_quote.time)
            monitor(db, settings, exit_quote.time)
        with Session(engine) as db:
            assert reconcile(db, exit_quote.time)
            orders = db.scalars(select(OrderRow)).all()
            account = db.get(Account, "PAPER")
            assert all(o.state == "CLOSED" for o in orders)
            assert account.balance == money(D(10000) + sum((o.pnl for o in orders), D(0)))
            assert account.equity == account.balance
    assert len(orders) == 30


def test_financing_rounding_is_independent_of_monitor_frequency(store):
    engine, candidate, quote, settings, now = store
    settings = settings.model_copy(update={"paper_financing_per_unit_per_bar": D(".00001")})
    with Session(engine) as db:
        submit(db, candidate, quote, settings, now)
        # Isolate sub-ledger-precision accrual, as can occur with fractional crypto quantities.
        order = db.get(OrderRow, candidate.id)
        order.units = D(".000001")
        db.commit()
    for bar in range(1, 11):
        with Session(engine) as db:
            monitor(db, settings, now + timedelta(seconds=300 * bar))
    with Session(engine) as db:
        order = db.get(OrderRow, candidate.id)
        assert order.financing_bars == 10
        assert order.fees_paid == money(D(".000001") * D(".00001") * 10) == D(".0000000001")
        assert db.get(Account, "PAPER").balance == D(10000) - order.fees_paid


@pytest.mark.parametrize("state", ["PROPOSED", "RISK_APPROVED", "SUBMITTING", "UNKNOWN"])
def test_incomplete_order_states_suspend_restart(store, state):
    engine, candidate, quote, settings, now = store
    with Session(engine) as db:
        submit(db, candidate, quote, settings, now)
        db.get(OrderRow, candidate.id).state = state
        db.commit()
        assert not reconcile(db, now)
        assert db.get(Account, "PAPER").suspended
