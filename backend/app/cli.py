import argparse
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import select

from app.core.config import get_settings
from app.database.bootstrap import bootstrap
from app.database.session import SessionLocal
from app.market_data.fixtures import demo_candles
from app.market_data.providers import CoinbaseData, OandaData
from app.market_data.store import ingest, insert_candles, load_candles
from app.models.tables import Event, Instrument, ModelVersion, SignalRow
from app.strategies.registry import evaluate


def init(demo=False, demo_count=360):
    if not 60 <= demo_count <= 10000:
        raise ValueError("Demo candle count must be between 60 and 10000")
    with SessionLocal() as db:
        bootstrap(db)
        if demo:
            for instrument in db.scalars(select(Instrument)).all():
                for timeframe in (60, 300, 900, 3600):
                    rows = demo_candles(instrument.symbol, timeframe, demo_count)
                    insert_candles(db, rows, datetime.now(timezone.utc))
                    when = rows[-1].time + timedelta(seconds=timeframe)
                    for candidate in evaluate(rows, when, instrument.tick_size):
                        if not db.get(SignalRow, candidate.id):
                            db.add(
                                SignalRow(
                                    id=candidate.id,
                                    time=candidate.time,
                                    symbol=candidate.symbol,
                                    strategy=candidate.strategy,
                                    status="REJECTED",
                                    payload=candidate.model_dump(mode="json"),
                                    reasons=["SYNTHETIC_FIXTURE", "NO_VALIDATED_CALIBRATED_MODEL"],
                                )
                            )
            db.add(Event(kind="demo_initialized", detail={"source": "synthetic", "live_prices": False}))
        db.commit()


async def download(args):
    settings = get_settings()
    with SessionLocal() as db:
        instrument = db.get(Instrument, args.symbol)
        if not instrument:
            raise ValueError("Unknown instrument; run init first")
        async with httpx.AsyncClient(timeout=30) as client:
            provider = OandaData(settings, client) if instrument.provider == "oanda" else CoinbaseData(client)
            print(
                await ingest(
                    db,
                    provider,
                    args.symbol,
                    args.timeframe,
                    datetime.fromisoformat(args.start),
                    datetime.fromisoformat(args.end),
                    args.resume,
                )
            )


def main():
    parser = argparse.ArgumentParser(prog="aegis")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--demo-count", type=int, default=360)
    for name in ("activate-paper", "rollback-paper", "deactivate-paper"):
        p = commands.add_parser(name)
        p.add_argument("identifier", help="Model version for activation; deployment ID otherwise")
        if name == "activate-paper":
            p.add_argument("--review", required=True)
        p.add_argument("--operator", required=True)
        p.add_argument("--reason", required=True)
    p = commands.add_parser("paper-record-start")
    p.add_argument("--symbols", nargs="+", required=True)
    p.add_argument("--trial-policy")
    p = commands.add_parser("trial-policy")
    p.add_argument("--models", nargs="*", default=[])
    p.add_argument("--output", required=True)
    p = commands.add_parser("trial-approve")
    p.add_argument("policy")
    p.add_argument("--operator", required=True)
    p.add_argument("--reason", required=True)
    p = commands.add_parser("trial-report")
    p.add_argument("run_id")
    p.add_argument("--output", required=True)
    p = commands.add_parser("practice-check")
    p.add_argument("--symbols", nargs="+", default=["EUR_USD", "GBP_USD"])
    p.add_argument("--output", required=True)
    for name in ("paper-record-stop", "paper-record-report"):
        p = commands.add_parser(name)
        p.add_argument("run_id")
    commands.add_parser("acceptance-policy")
    p = commands.add_parser("assess-model")
    p.add_argument("version")
    p.add_argument("--artifacts", default="model_artifacts")
    p = commands.add_parser("shadow")
    p.add_argument("version")
    p.add_argument("--artifacts", default="model_artifacts")
    p = commands.add_parser("replay-shadow")
    p.add_argument("version")
    p.add_argument("--artifacts", default="model_artifacts")
    p.add_argument("--limit", type=int, default=200)
    p = commands.add_parser("backtest-model")
    p.add_argument("version")
    p.add_argument("--partition", choices=["validation", "test"], default="validation")
    p.add_argument("--artifacts", default="model_artifacts")
    p.add_argument("--output", required=True)
    p = commands.add_parser("train-candidates")
    p.add_argument("--symbol", default="EUR_USD")
    p.add_argument("--source", required=True)
    p.add_argument("--timeframe", type=int, default=300)
    p.add_argument("--strategy", default="trend")
    p.add_argument("--spread", required=True, help="Explicit assumed full bid/ask spread")
    p.add_argument("--slippage", required=True, help="Explicit adverse slippage per fill")
    p.add_argument("--fee-rate", required=True, help="Explicit per-side notional fee rate")
    p.add_argument("--financing-per-bar", default="0", help="Explicit per-unit financing assumption")
    p.add_argument("--output", default="model_artifacts")
    p.add_argument("--family", choices=["logistic", "lightgbm", "xgboost"], default="logistic")
    p.add_argument("--start", help="Inclusive UTC dataset boundary")
    p.add_argument("--end", help="Exclusive UTC dataset boundary")
    p = commands.add_parser("data-report")
    p.add_argument("--symbol", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--timeframe", type=int, default=300)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--output", required=True)
    for command in ("download", "train", "export"):
        p = commands.add_parser(command)
        p.add_argument("--symbol", default="EUR_USD")
        p.add_argument("--timeframe", type=int, default=300)
        if command == "download":
            p.add_argument("--start", required=True, help="ISO-8601 UTC including +00:00")
            p.add_argument("--end", required=True)
            p.add_argument("--resume")
        else:
            p.add_argument("--source", default="fixture")
            p.add_argument(
                "--output",
                default="model_artifacts" if command == "train" else "data/processed/candles.parquet",
            )
        if command == "train":
            p.add_argument("--family", choices=["logistic", "lightgbm", "xgboost"], default="logistic")
    commands.add_parser("backtest-demo")
    args = parser.parse_args()
    if args.command in ("activate-paper", "rollback-paper", "deactivate-paper"):
        from app.machine_learning.deployment import activate, deactivate, rollback

        settings, now = get_settings(), datetime.now(timezone.utc)
        with SessionLocal() as db:
            if args.command == "activate-paper":
                result = activate(
                    db,
                    args.identifier,
                    args.review,
                    Path(settings.model_artifact_dir),
                    settings,
                    args.operator,
                    args.reason,
                    now,
                )
            elif args.command == "rollback-paper":
                result = rollback(
                    db,
                    args.identifier,
                    Path(settings.model_artifact_dir),
                    settings,
                    args.operator,
                    args.reason,
                    now,
                )
            else:
                deactivate(db, args.identifier, args.operator, args.reason)
                result = args.identifier
            print(
                json.dumps({"deployment": result, "action": args.command, "broker_execution_allowed": False})
            )
    elif args.command == "practice-check":
        from app.brokers.oanda import OandaPractice
        from app.brokers.validation import readiness_report

        async def check():
            settings = get_settings().model_copy(update={"trading_mode": "OANDA_PRACTICE", "demo_mode": False})
            async with httpx.AsyncClient(timeout=30) as client:
                return await readiness_report(OandaPractice(settings, client), settings.oanda_account_id, args.symbols)

        path = Path(args.output)
        if path.exists():
            raise ValueError("Practice readiness reports are immutable; use a new output path")
        report = asyncio.run(check())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    elif args.command == "trial-policy":
        from app.execution.trials import proposed_policy

        path = Path(args.output)
        if path.exists():
            raise ValueError("Trial proposals are immutable; use a new output path")
        path.parent.mkdir(parents=True, exist_ok=True)
        policy = proposed_policy(get_settings(), args.models)
        path.write_text(json.dumps(policy, indent=2), encoding="utf-8")
        print(json.dumps(policy, indent=2))
    elif args.command == "trial-approve":
        from app.execution.trials import approve_policy

        with SessionLocal() as db:
            print(approve_policy(db, json.loads(Path(args.policy).read_text()), get_settings(),
                                 args.operator, args.reason, datetime.now(timezone.utc)))
    elif args.command == "trial-report":
        from app.execution.trials import trial_report

        with SessionLocal() as db:
            report = trial_report(db, args.run_id, datetime.now(timezone.utc))
            path = Path(args.output)
            if path.exists():
                raise ValueError("Trial reports are immutable; use a new output path")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
    elif args.command.startswith("paper-record-"):
        from app.execution.recorder import run_report, start_run, stop_run

        with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            if args.command == "paper-record-start":
                print(json.dumps({"run_id": start_run(db, get_settings(), args.symbols, now, args.trial_policy)}))
            elif args.command == "paper-record-stop":
                stop_run(db, args.run_id, now)
                print(json.dumps({"run_id": args.run_id, "status": "STOPPED"}))
            else:
                print(json.dumps(run_report(db, args.run_id, now), indent=2))
    elif args.command == "acceptance-policy":
        from app.machine_learning.policy import acceptance_policy

        print(json.dumps(acceptance_policy(get_settings()), indent=2))
    elif args.command == "assess-model":
        from app.machine_learning.assessment import assess_model

        with SessionLocal() as db:
            print(json.dumps(assess_model(db, args.version, Path(args.artifacts), get_settings()), indent=2))
    elif args.command == "init":
        init(args.demo, args.demo_count)
        print("Database initialized" + (" with SYNTHETIC fixtures" if args.demo else ""))
    elif args.command == "shadow":
        from app.machine_learning.registry import deploy_shadow

        with SessionLocal() as db:
            print(deploy_shadow(db, args.version, Path(args.artifacts)))
    elif args.command == "replay-shadow":
        from app.machine_learning.replay import replay_shadow

        with SessionLocal() as db:
            model = db.get(ModelVersion, args.version)
            if not model:
                raise ValueError("Unknown model version")
            metadata = model.metadata_json
            rows = load_candles(db, metadata["symbol"], metadata["timeframe"], metadata["source"], 1_000_000)
            print(json.dumps(replay_shadow(db, rows, args.version, Path(args.artifacts), args.limit)))
    elif args.command == "backtest-model":
        from app.backtesting.registered import evaluate_registered

        output = Path(args.output)
        if output.exists():
            raise ValueError("Report already exists; preserve prior research results")
        with SessionLocal() as db:
            report = evaluate_registered(
                db, args.version, Path(args.artifacts), get_settings(), args.partition
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as file:
                json.dump(report, file, indent=2)
            print(
                json.dumps(
                    {
                        "report": str(output),
                        "trades": report["metrics"]["trades"],
                        "execution_authorized": False,
                        "partition": args.partition,
                    }
                )
            )
    elif args.command == "data-report":
        from app.market_data.coverage import coverage_report

        start, end = datetime.fromisoformat(args.start), datetime.fromisoformat(args.end)
        with SessionLocal() as db:
            rows = load_candles(db, args.symbol, args.timeframe, args.source, 1_000_000, start=start, end=end)
            report = coverage_report(rows, start, end, datetime.now(timezone.utc))
            path = Path(args.output)
            if path.exists():
                raise ValueError("Coverage reports are immutable; use a new output path")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps({k: v for k, v in report.items() if k not in ("quality", "unexplained_missing_timestamps")}, indent=2))
    elif args.command == "train-candidates":
        from decimal import Decimal

        from app.backtesting.simulator import FillAssumptions
        from app.machine_learning.candidate_training import train_candidates

        with SessionLocal() as db:
            instrument = db.get(Instrument, args.symbol)
            if instrument is None:
                raise ValueError("Unknown instrument")
            start = datetime.fromisoformat(args.start) if args.start else None
            end = datetime.fromisoformat(args.end) if args.end else None
            rows = load_candles(db, args.symbol, args.timeframe, args.source, 1_000_000, start=start, end=end)
            report = train_candidates(
                rows,
                instrument.tick_size,
                args.strategy,
                FillAssumptions(Decimal(args.spread), Decimal(args.slippage), Decimal(args.fee_rate),
                                Decimal(args.financing_per_bar)),
                Path(args.output),
                args.family,
                settings=get_settings(),
            )
            db.add(ModelVersion(id=report["version"], metadata_json=report, status="EXPERIMENTAL"))
            db.commit()
            print(json.dumps(report, indent=2))
    elif args.command == "download":
        asyncio.run(download(args))
    elif args.command in ("train", "export"):
        with SessionLocal() as db:
            rows = load_candles(db, args.symbol, args.timeframe, args.source, 1_000_000)
            if not rows:
                raise ValueError("No data for requested source/instrument/timeframe")
            if args.command == "train":
                from app.machine_learning.training import train

                report = train(rows, Path(args.output), args.family)
                db.add(ModelVersion(id=report["version"], metadata_json=report, status="EXPERIMENTAL"))
                db.commit()
                print(json.dumps(report, indent=2))
            else:
                from app.indicators.features import frame

                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                frame(rows).to_parquet(output, compression="zstd")
                print(str(output))
    elif args.command == "backtest-demo":
        from decimal import Decimal as D

        from app.backtesting.simulator import FillAssumptions, metrics, simulate_trade

        rows = demo_candles(count=360)
        pnls, trades = [], []
        for i in range(60, 340, 15):
            candidates = evaluate(rows[:i], rows[i].time, D(".00001"), enabled=["trend"])
            if candidates:
                s = candidates[0]
                trade = simulate_trade(
                    rows[i : i + 12],
                    s.direction,
                    s.entry,
                    s.stop,
                    s.target,
                    D(100),
                    FillAssumptions(D(".0002"), D(".00001")),
                )
                trades.append(trade)
                pnls.append(float(trade["pnl"]))
        print(
            json.dumps(
                {
                    "source": "SYNTHETIC SOFTWARE DEMONSTRATION",
                    "evidence_of_profitability": False,
                    "trades": trades,
                    "metrics": metrics(pnls),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
