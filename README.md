# AegisTrade AI

A local Forex and cryptocurrency research workspace with FastAPI, React, causal strategies, model experiments, independent risk checks and persistent paper execution.

**This is an initial working implementation, not the completed autonomous platform in Prompt.md.** No trading advantage has been established. The demo uses labeled synthetic candles and simulated USD capital. Live execution is unsupported. Practice submission is disabled while its gateway is incomplete. See [CODEX_PROGRESS.md](CODEX_PROGRESS.md) for exact acceptance gaps.

## Docker quick start

Requires Docker Desktop with its Linux engine running. From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env  # first setup only; preserve an existing .env
docker compose up --build -d
docker compose exec backend python -m app.cli init --demo
```

Open **http://localhost:5173**. API documentation: **http://localhost:8000/docs**. Health endpoints: `/health/live` and `/health/ready`.

Compose runs PostgreSQL, a migration job, backend, frontend, trading worker and market-data worker. Named volumes preserve the database, research files and model artifacts. Workers stay offline by default.

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
```

The Model lab displays stored experimental shadow probabilities. Replay never submits an order. Portfolio replay verifies the original input candles and reuses the risk engine; zero qualifying trades is a valid result. Existing artifacts and reports are not overwritten. Preserve the final test partition for a predeclared evaluation rather than repeated tuning. The older `train` command is a directional diagnostic whose artifacts cannot be deployed to shadow.

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

## Current capabilities

- Read-only dashboard with charts, market/timeframe selection, signal inspection/filtering, journal with fees, strategies, shadow predictions, risk and health.
- Paginated history adapters, validated storage, resumable jobs, quote streams and reconnect loops.
- Six causal strategies, rule-based regimes, delayed swings and higher-timeframe alignment.
- Decimal sizing capped by available margin/exposure, loss limits, source/freshness checks, and durable paper orders with persisted fee/slippage assumptions.
- Conservative single-trade and single-instrument portfolio simulation, candidate-aligned labels, purged research partitions, calibration, verified artifacts and shadow replacement/retirement.
- Practice account inspection, narrative-only LLM and Telegram outbox components.

**Execution stays idle without execution-validated models.** The worker loads explicitly deployed SHADOW models for observation only. No ACTIVE promotion path exists. Demo signals are rejected; synthetic model probabilities are labeled experimental. Multi-asset research, execution-model promotion, broker reconciliation, notification orchestration and operational hardening remain incomplete.

## Documentation

[Architecture](docs/ARCHITECTURE.md) · [Data](docs/DATA_PIPELINE.md) · [Strategies](docs/TRADING_STRATEGIES.md) · [Models](docs/MODEL_TRAINING.md) · [Backtesting](docs/BACKTESTING.md) · [Risk](docs/RISK_MANAGEMENT.md) · [Broker](docs/BROKER_INTEGRATION.md) · [Operations](docs/OPERATIONS.md) · [Security](docs/SECURITY.md) · [Live readiness](docs/LIVE_TRADING_READINESS.md)
