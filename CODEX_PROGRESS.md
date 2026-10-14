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

Foundation and research/paper components are runnable. Phase 7 now includes transaction fault coverage, concurrent account-risk reservation checks, accelerated restart replay and persisted research acceptance reports with predeclared policy. Candidate-aligned labels, trusted shadow loading, portfolio replay and durable paper costs remain integrated. The entire Prompt.md platform is not complete.

Verified on October 14, 2026 (America/Winnipeg): 82 backend tests passed, including PostgreSQL cases (none skipped); 3 frontend tests passed; TypeScript/Vite production build passed; Ruff passed. SQLite legacy-order migration preservation and PostgreSQL migration 0004/schema check passed. Docker stack built and started; API/readiness/Nginx proxy and worker heartbeats verified. Coinbase public history previously downloaded 288 real BTC/USD candles; a public WebSocket quote was received. The database contains 32,000 explicitly synthetic fixture candles, separate from provider data. Two experiment versions each recorded 139 historical shadow observations, and held-out portfolio replay returned zero trades at the unchanged 80% threshold. These synthetic results establish software behavior only.

Current shadow version: `candidate-logistic-1894f324bd38fc28`. Its original 2,000-candle EUR/USD input manifest was verified before replay; prior shadow version was retired. Latest immutable report in the research volume: `data/reports/synthetic-validation-verified.json`. Models, data, reports and secrets are excluded from Git.

Paper restart tests verify entry/exit fees, financing deduplication, preserved costs after configuration changes and rejection of mismatched-provider quotes. Tests use explicitly labeled test-only execution eligibility; no production model was activated. Backend warnings are a Starlette HTTPX deprecation and a sparse-class warning in the legacy synthetic calibration test.

New fault coverage: six simultaneous duplicate/distinct submissions, crashes before/after commit, replayed failed exits, rollover gaps, polling-independent financing rounding, incomplete order states, and 30-cycle accelerated restart replay on both SQLite and PostgreSQL. Test configuration strips application credentials and settings before collection. PostgreSQL tests use only randomly named schemas through the explicit TEST_POSTGRES_URL; they are skipped when that variable is absent. This is not a sustained real-time soak.

New assessed experiment: `candidate-logistic-51e77153ad1f8ef4`, with policy `research-screen-v1`. Review `cbc5ccacff1e2ca85ab920c84bb3c6f04fda0deeef7f987a88abbc0caec69a00` is REJECTED for synthetic source, short history and 189 calibration samples (minimum 200). Artifact integrity and policy matching passed. Reviews are idempotent and do not promote models. Full acceptance methodology and limitations are in docs/MODEL_ACCEPTANCE.md.

Implemented: configuration/live-disable gates, database/migrations, historical and quote adapters, quality checks, causal features/six strategy hypotheses/regimes, conservative single-trade simulator, experimental calibrated training, deterministic Decimal risk, durable paper lifecycle, React dashboard, Docker and documentation under docs/.

External integration status: supplied credentials were preserved in ignored local `.env`, and tracked `.env.example` placeholders were restored. A read-only EUR/USD history request to OANDA's practice endpoint returned HTTP 401; valid practice credentials and an account ID are still needed for verification. DeepSeek, Telegram and optional LightGBM/XGBoost remain externally unverified. Practice submission remains disabled pending durable broker reconciliation and account/instrument validation. No real-money order, practice order, LLM request or Telegram message has been sent. Browser visual verification is unavailable because no browser is connected.

GitHub delivery: backend, dashboard and deployment/docs were committed separately and pushed to `Qteneqja/TraderBot3000` on `main`. [GitHub verification run 38517521949](https://github.com/Qteneqja/TraderBot3000/actions/runs/38517521949) passed both jobs, including 50 backend tests, 3 frontend tests, production build, Ruff and PostgreSQL migrations. CI actions were subsequently updated to official v7 releases pinned by commit, with an explicit Ubuntu 24.04 runner and read-only repository permissions, to address the run's deprecated-runtime warning.

Remaining acceptance gaps include multi-asset portfolio replay and statistical robustness; execution-model promotion/rollback and real-market evidence; autonomous paper soak tests; practice execution/reconciliation; verified sessions/economic calendar; notification orchestration; drift/retraining; fuller analytics and operational/security hardening. Shadow replacement/retirement is implemented; no execution promotion path exists. No trading advantage has been established. Live execution remains unsupported.

Run from the repository root: `docker compose up --build -d`, then `docker compose exec backend python -m app.cli init --demo`. Dashboard: http://localhost:5173. API: http://localhost:8000/docs. See README for tests and research commands.

Next development task: implement account-scoped deployment/rollback with runtime evidence checks and a real-time paper soak recorder, then durable OANDA practice reservations/transaction reconciliation. Research screening is implemented; no ACTIVE promotion path exists. Missing valid practice credentials do not block offline engineering, but prevent external OANDA verification.
