# AegisTrade AI

A local Forex and cryptocurrency research workspace with FastAPI, React, causal strategies, model experiments, independent risk checks and persistent paper execution.

**No trading advantage has been established; autonomous model entry remains inactive.** Current provider feeds and candidate research run separately from labeled fixtures. Durable practice execution is implemented and fault-tested, but submission stays disabled pending qualification and external lifecycle acceptance. Live execution is unsupported. See the [activation report](docs/TRADING_ACTIVATION_REPORT.md), [exact qualification results](docs/FINAL_MODEL_QUALIFICATION_REPORT.md) and [CODEX_PROGRESS.md](CODEX_PROGRESS.md) for actual status.

## Docker quick start

Requires Docker Desktop with its Linux engine running. From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env  # first setup only; preserve an existing .env
docker compose up --build -d
docker compose exec backend python -m app.cli init --demo
```

Open **http://localhost:5173**. API documentation: **http://localhost:8000/docs**. Health endpoints: `/health/live` and `/health/ready`.

Compose runs PostgreSQL, a migration job, backend, frontend, market/trading workers, candidate-learning worker and isolated narrative worker. Named volumes preserve the database, research files and model artifacts. Example configuration defaults to fixtures and disables external narratives/notifications; current local provider settings are separate and ignored.

For alternate ports, set `$env:FRONTEND_PORT='5174'` and `$env:BACKEND_PORT='8001'` before Compose. Only loopback ports are published.

```powershell
docker compose logs --tail 100 backend trading-worker market-data-worker
docker compose stop
```

## Direct Windows development

Python 3.12+ and Node 22+ are required. `npm.cmd` avoids PowerShell's npm script policy restriction.

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock
.venv/Scripts/python.exe -m pip install --no-deps -e backend
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m app.cli init --demo
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal at the repository root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Direct development uses `backend/aegis.db` (SQLite); Compose uses PostgreSQL. Direct commands above read `backend/.env` if present. The root `.env` is for Compose. For provider credentials in direct development, create `backend/.env` with the required settings and an appropriate DATABASE_URL. Both are ignored by Git. Linux/macOS equivalents use `python3`, `.venv/bin/python` and `npm`.

## Research commands

Run these from `backend/`. In Compose, replace `../.venv/Scripts/python.exe` with `docker compose exec backend python` from the repository root.

```powershell
../.venv/Scripts/python.exe -m app.cli download --symbol BTC-USD --timeframe 300 --start 2025-01-01T00:00:00+00:00 --end 2025-01-02T00:00:00+00:00
# Forex requires OANDA_API_KEY; use a practice account.
../.venv/Scripts/python.exe -m app.cli download --symbol EUR_USD --timeframe 300 --start 2025-01-06T00:00:00+00:00 --end 2025-01-07T00:00:00+00:00
# Add --resume JOB_ID after an interrupted download.
../.venv/Scripts/python.exe -m app.cli train --symbol EUR_USD --source fixture --output model_artifacts
../.venv/Scripts/python.exe -m app.cli backtest-demo
../.venv/Scripts/python.exe -m app.cli export --symbol EUR_USD --source fixture --output data/processed/eurusd-fixture.parquet
# Set DEMO_MODE=false for real provider ingestion. This does not enable broker execution.
../.venv/Scripts/python.exe -m app.worker market
../.venv/Scripts/python.exe -m app.worker trading
```

Use `--source oanda` or `--source coinbase` for provider datasets. Training creates immutable EXPERIMENTAL artifacts, never an active model. Insufficient data/classes produce errors. Optional research families: install `pip install -e '.[research]'` inside `backend/`, then select `--family lightgbm` or `--family xgboost`. These families have not been validated in the initial session.

Candidate-specific shadow workflow (repository root, Docker):

```powershell
docker compose exec backend python -m app.cli init --demo --demo-count 2000
docker compose exec backend python -m app.cli train-candidates --symbol EUR_USD --source fixture --strategy trend --spread 0.00002 --slippage 0.00001 --fee-rate 0
# Replace VERSION with the version printed by training. Costs above are synthetic demo assumptions.
docker compose exec backend python -m app.cli shadow VERSION
docker compose exec backend python -m app.cli replay-shadow VERSION --limit 200
docker compose exec backend python -m app.cli backtest-model VERSION --partition validation --output data/reports/validation.json
docker compose exec backend python -m app.cli acceptance-policy
docker compose exec backend python -m app.cli assess-model VERSION
```

The Model lab displays stored experimental shadow probabilities. Replay never submits an order. Portfolio replay verifies the original input candles and reuses the risk engine; zero qualifying trades is a valid result. Existing artifacts and reports are not overwritten. Preserve the final test partition for a predeclared evaluation rather than repeated tuning. The older `train` command is a directional diagnostic whose artifacts cannot be deployed to shadow.

New candidate artifacts bind the research screening policy and risk settings before fitting. Assessment stores an immutable, deduplicated report visible in Model lab. Synthetic data, short histories, changed policies and insufficient samples fail screening. Qualifying research is checked against baseline predictions, portfolio economics, uncertainty and doubled costs. Passing research checks never activates a model. Explicit paper-trial activation/rollback and an operational recorder are available; sustained real-time evidence remains outstanding. See [paper trial commands](docs/PAPER_TRIALS.md). See [acceptance methodology](docs/MODEL_ACCEPTANCE.md).

## Tests

From the repository root:

```powershell
.venv/Scripts/python.exe -m pytest backend/tests -q
.venv/Scripts/python.exe -m ruff check backend
cd frontend
npm.cmd test
npm.cmd run build
```

Linux container fallback for Windows scientific-library issues (repository root):

```powershell
docker compose run --rm --no-deps --volume "${PWD}/backend:/work" --workdir /work -e PYTHONPATH=/work backend python -m pytest tests -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/verify_stack.py
```

Tests need no paid APIs, credentials or real money. Backend versions are pinned in `backend/requirements.lock`; frontend versions in `package-lock.json`.

The fault suite runs on SQLite and, when `TEST_POSTGRES_URL` is set, a dedicated randomly named PostgreSQL schema per case. The account in that URL must be able to create test schemas. CI provides a disposable database. Without this variable, PostgreSQL cases are explicitly skipped; do not count them as passed. These accelerated tests do not replace a sustained real-time soak.

## Current capabilities

- Read-only dashboard with charts, market/timeframe selection, signal inspection/filtering, journal with fees, strategies, shadow predictions, risk and health.
- Paginated history adapters, validated storage, resumable jobs, quote streams and reconnect loops.
- Six causal strategies, rule-based regimes, delayed swings and higher-timeframe alignment.
- Decimal sizing capped by available margin/exposure, loss limits, source/freshness checks, and durable paper orders with persisted fee/slippage assumptions.
- Conservative single-trade and single-instrument portfolio simulation, candidate-aligned labels, purged research partitions, calibration, verified artifacts and shadow replacement/retirement.
- Practice account inspection, [bounded DeepSeek commentary](docs/LLM_INTEGRATION.md) with an isolated worker and read-only dashboard, plus Telegram outbox components. External LLM sharing must be approved before enabling.

**Execution stays idle without an eligible, explicitly approved paper deployment.** Account-scoped activation, rollback and deactivation bind research evidence to runtime inference and risk checks. No current model qualifies. Formal paper trial policies and daily/weekly reports are implemented; sustained model performance remains unverified. A durable OANDA practice gateway is mocked/fault-tested and read-only reconciliation is externally verified; actual order submission remains disabled pending the [broker acceptance sequence](docs/BROKER_INTEGRATION.md). [Controlled learning](docs/CONTROLLED_LEARNING.md) records attributed outcomes, monitors drift and schedules experimental CPU-family comparisons without activation. Prospective frozen-model final evaluation is implemented with disjoint future reservations and no refitting or automatic activation. The original sixteen trend candidates failed validation; the corrected-code campaign completed without an eligible model; see [measured results](docs/RESEARCH_RESULTS.md). Verified executable costs, a qualified model, sustained paper/practice trials and further research/hardening remain outstanding. Real-money execution is unsupported.

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Data](docs/DATA_PIPELINE.md) · [Strategies](docs/TRADING_STRATEGIES.md) · [Models](docs/MODEL_TRAINING.md) · [Backtesting](docs/BACKTESTING.md) · [Risk](docs/RISK_MANAGEMENT.md) · [Broker](docs/BROKER_INTEGRATION.md) · [Operations](docs/OPERATIONS.md) · [Security](docs/SECURITY.md) · [Live readiness](docs/LIVE_TRADING_READINESS.md)
