# AegisTrade AI implementation progress

This repository started with only Prompt.md and a title-only README. No existing application was replaced.

## Implementation sequence and dependencies

1. Foundation: configuration, persistent schema, migrations, API health, Docker, dashboard shell.
2. Market data: typed candles/quotes, quality validation, provider adapters, durable ingestion, streams.
3. Research: causal features, strategy registry, regime analysis.
4. Simulation: conservative fills, Decimal sizing, risk restrictions, metrics.
5. ML: purged chronological splits, barrier labels, calibrated baselines, candidate registry.
6. Optimization: deterministic entry/stop/target and approval decisions.
7. Paper execution: durable idempotency, risk locking, position exits, journal, worker.
8. Practice: OANDA transport and reconciliation; external verification requires credentials.
9. Explanation/notifications: isolated LLM and Telegram adapters.
10. Dashboard: database-backed research, signals, portfolio, risk and health.
11. Hardening: failure tests, startup checks, operating documentation.
12. Readiness: document unresolved validation; real-money execution remains unsupported.

## Current checkpoint

Foundation and research/paper components are runnable. Phase 7 integration now includes candidate-aligned labels, trusted shadow loading, persistent predictions, single-instrument portfolio replay using the shared risk engine, and durable paper cost accounting. The entire Prompt.md platform is not complete.

Verified on October 14, 2026 (America/Winnipeg): 50 backend tests passed; 3 frontend tests passed; TypeScript/Vite production build passed; Ruff passed. SQLite legacy-order migration preservation and PostgreSQL migration 0003/schema check passed. Docker stack built and started; API/readiness/Nginx proxy and worker heartbeats verified. Coinbase public history downloaded 288 real BTC/USD candles; a public WebSocket quote was received. The database now contains 32,000 explicitly synthetic fixture candles, separate from provider data. Candidate training completed; two experiment versions each recorded 139 historical shadow observations, and held-out portfolio replay returned zero trades at the unchanged 80% threshold. These synthetic results establish software behavior only.

Current shadow version: `candidate-logistic-1894f324bd38fc28`. Its original 2,000-candle EUR/USD input manifest was verified before replay; prior shadow version was retired. Latest immutable report in the research volume: `data/reports/synthetic-validation-verified.json`. Models, data, reports and secrets are excluded from Git.

Paper restart tests verify entry/exit fees, financing deduplication, preserved costs after configuration changes and rejection of mismatched-provider quotes. Tests use explicitly labeled test-only execution eligibility; no production model was activated. Backend warnings are a Starlette HTTPX deprecation and a sparse-class warning in the legacy synthetic calibration test.

Implemented: configuration/live-disable gates, database/migrations, historical and quote adapters, quality checks, causal features/six strategy hypotheses/regimes, conservative single-trade simulator, experimental calibrated training, deterministic Decimal risk, durable paper lifecycle, React dashboard, Docker and documentation under docs/.

Unverified external integrations: OANDA practice credentials, DeepSeek, Telegram and optional LightGBM/XGBoost. Practice submission remains disabled pending durable broker reconciliation and account/instrument validation. No real-money order, practice order, LLM request or Telegram message has been sent. Browser visual verification is unavailable because no browser is connected. CI is defined but has not run remotely.

Remaining acceptance gaps include multi-asset portfolio replay and statistical robustness; execution-model promotion/rollback and real-market evidence; autonomous paper soak tests; practice execution/reconciliation; verified sessions/economic calendar; notification orchestration; drift/retraining; fuller analytics and operational/security hardening. Shadow replacement/retirement is implemented; no execution promotion path exists. No trading advantage has been established. Live execution remains unsupported.

Run from the repository root: `docker compose up --build -d`, then `docker compose exec backend python -m app.cli init --demo`. Dashboard: http://localhost:5173. API: http://localhost:8000/docs. See README for tests and research commands.

Next development task: expand paper fault/soak coverage and define reproducible execution-model acceptance/promotion gates using real-market validation evidence; then implement durable OANDA practice reservations and transaction reconciliation. Missing credentials do not block those offline engineering tasks.
