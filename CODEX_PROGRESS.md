# AegisTrade AI implementation progress

## Full-year provider history backfill (October 14, 2026 UTC)

Completed the operator-requested five-minute backfill for 2025-10-14 00:00 through 2026-10-14 00:00 UTC: EUR_USD/oanda 74,589 candles, GBP_USD/oanda 74,577, BTC-USD/coinbase 104,971 and ETH-USD/coinbase 104,971 (359,108 total within the requested interval). All four durable ingestion jobs are COMPLETE. Audit found zero invalid OHLC/volume/completeness/alignment rows and bid/ask components on every Forex row. Targeted provider requests did not recover the short gaps; each crypto series has 149 absent intervals. Forex calendar/closure classification remains unverified. No candles were invented. The full coverage/gap/hash report is saved in the research volume and ignored local data/reports folder; docs/HISTORICAL_DATA.md records scope, counts and job IDs. The dashboard's 300-candle window does not limit training's separate database query. Existing older provider samples remain preserved outside the audited interval.

Verification: 117 backend tests passed including PostgreSQL cases, 9 frontend tests passed, production build passed, Alembic schema check and stack smoke checks passed. Application code/settings were unchanged. No model trained or activated; zero orders. Next: review provider execution-quality and cost assumptions, explicitly define the dataset for chronological training, and assess real-market models under the existing policy. Sufficient duration is not research approval or broker readiness.

## TradingView diagnostic (October 14, 2026 UTC)

Tested the user-requested rongardF/tvdatafeed library at commit e6f6aaa7de439ac6e454d9b26d2760ded8dc4923 in an ignored isolated Python environment. Anonymous downloads returned 1,000 hourly NSE:NIFTY bars, 5,000 five-minute OANDA:EURUSD bars and 5,000 five-minute COINBASE:BTCUSD bars. The latter two span only 23.36 and 17.36 calendar days, below the 180-day research minimum. Added a bounded metadata-only diagnostic script and docs/TRADINGVIEW_DATA.md. Optional login reads local ignored credentials; authenticated access remains externally unverified. No application data, production dependencies, deployments or orders were changed. Returned timestamps are host-local naive values and the data has not been validated or imported for training.

Verification: the final anonymous probe retrieved all three requested datasets; 117 backend tests passed including PostgreSQL cases, 9 frontend tests passed, TypeScript/Vite build passed, Alembic schema check reported no new operations, and probe Ruff/compilation checks passed. Frontend bundling first encountered sandbox ancestor-directory access denial, then passed with approved execution outside that sandbox. Existing backend warnings remain unchanged. Authenticated retrieval and future TradingView ingestion remain unverified/unsupported respectively.

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

Foundation and research/paper components are runnable. Phase 7 now includes account-scoped PAPER activation/replacement/rollback/deactivation, evidence-bound runtime inference, and a persistent operational recorder. Deployment approval is separate from immutable research artifacts; no current model qualifies. Existing transaction fault coverage, concurrent account-risk reservation, shadow inference, portfolio replay and predeclared research screening remain integrated. The entire Prompt.md platform is not complete.

Previous checkpoint on October 14, 2026: 82 backend tests passed, including PostgreSQL cases (none skipped); 3 frontend tests passed; TypeScript/Vite production build passed; Ruff passed. SQLite legacy-order migration preservation and PostgreSQL migration 0004/schema check passed. Docker stack built and started; API/readiness/Nginx proxy and worker heartbeats verified. Coinbase public history previously downloaded 288 real BTC/USD candles; a public WebSocket quote was received. The database contains 32,000 explicitly synthetic fixture candles, separate from provider data. Two experiment versions each recorded 139 historical shadow observations, and held-out portfolio replay returned zero trades at the unchanged 80% threshold. These synthetic results establish software behavior only.

Current shadow version: `candidate-logistic-1894f324bd38fc28`. Its original 2,000-candle EUR/USD input manifest was verified before replay; prior shadow version was retired. Latest immutable report in the research volume: `data/reports/synthetic-validation-verified.json`. Models, data, reports and secrets are excluded from Git.

Paper restart tests verify entry/exit fees, financing deduplication, preserved costs after configuration changes and rejection of mismatched-provider quotes. Ledger/fault tests now explicitly mock the inference authorization boundary; deployment tests exercise the production gate separately. Positive research evidence is mocked in orchestration tests; real-artifact inference is also tested with synthetic data and mocked prior eligibility. No production model was activated. Backend warnings are a Starlette HTTPX deprecation and a sparse-class warning in the legacy synthetic calibration test.

New fault coverage: six simultaneous duplicate/distinct submissions, crashes before/after commit, replayed failed exits, rollover gaps, polling-independent financing rounding, incomplete order states, and 30-cycle accelerated restart replay on both SQLite and PostgreSQL. Test configuration strips application credentials and settings before collection. PostgreSQL tests use only randomly named schemas through the explicit TEST_POSTGRES_URL; they are skipped when that variable is absent. This is not a sustained real-time soak.

New assessed experiment: `candidate-logistic-51e77153ad1f8ef4`, with policy `research-screen-v1`. Review `cbc5ccacff1e2ca85ab920c84bb3c6f04fda0deeef7f987a88abbc0caec69a00` is REJECTED for synthetic source, short history and 189 calibration samples (minimum 200). Artifact integrity and policy matching passed. Reviews are idempotent and do not promote models. Full acceptance methodology and limitations are in docs/MODEL_ACCEPTANCE.md.

Implemented: configuration/live-disable gates, database/migrations, historical and quote adapters, quality checks, causal features/six strategy hypotheses/regimes, conservative single-trade simulator, experimental calibrated training, deterministic Decimal risk, durable paper lifecycle, React dashboard, Docker and documentation under docs/.

External integration status: supplied credentials were preserved in ignored local `.env`, and tracked `.env.example` placeholders were restored. After the operator updated credentials, read-only OANDA practice EUR/USD candle and account-summary requests both returned HTTP 200. Authentication and account access are verified; broker execution and reconciliation are not. DeepSeek, Telegram and optional LightGBM/XGBoost remain externally unverified. Practice submission remains disabled pending durable broker reconciliation and account/instrument validation. No real-money order, practice order, LLM request or Telegram message has been sent. Browser visual verification is unavailable because no browser is connected.

GitHub delivery: backend, dashboard and deployment/docs were committed separately and pushed to `Qteneqja/TraderBot3000` on `main`. [GitHub verification run 38517521949](https://github.com/Qteneqja/TraderBot3000/actions/runs/38517521949) passed both jobs, including 50 backend tests, 3 frontend tests, production build, Ruff and PostgreSQL migrations. CI actions were subsequently updated to official v7 releases pinned by commit, with an explicit Ubuntu 24.04 runner and read-only repository permissions, to address the run's deprecated-runtime warning.

Remaining acceptance gaps include multi-asset portfolio replay and statistical robustness; eligible real-market models and independent regime/cost validation; sustained paper trial acceptance; practice execution/reconciliation; verified sessions/economic calendar; notification orchestration; drift/retraining; fuller analytics and operational/security hardening. PAPER activation/rollback is implemented; broker promotion remains unsupported. No trading advantage has been established. Live execution remains unsupported.

Run from the repository root: `docker compose up --build -d`, then `docker compose exec backend python -m app.cli init --demo`. Dashboard: http://localhost:5173. API: http://localhost:8000/docs. See README for tests and research commands.

Next development task: collect sufficient real-market history using the working practice/public credentials, assess models under the predeclared policy, define sustained paper-trial acceptance, and gather real-time evidence. Continue durable OANDA practice reservations/transaction reconciliation before enabling any practice orders. The operational recorder does not automatically approve a model or broker execution.

## Paper deployment and recorder milestone (October 14, 2026 UTC)

Migration 0005 adds deployment history, unique account/scope slots, recorder runs and samples. Local operator commands bind a passing research review to artifact, dataset, risk, cost and instrument evidence. Rollback revalidates the previous target; deactivation leaves open-position monitoring intact. Runtime reconstructs canonical proposals from stored completed candles and computes probabilities itself before deterministic risk approval. Caller flags and legacy ACTIVE metadata cannot authorize orders.

Recorder commands start/stop/report a single PAPER run; worker cycles persist timestamps, worker identity, feed freshness, deployment/configuration checks, equity/cost/risk snapshots and errors. Healthy duration requires contiguous matching wall/monotonic intervals. Restarts, gaps, stale feeds, fixture mode, configuration changes and errors earn no healthy time. Summary queries aggregate in the database. The dashboard exposes current/historical trials and recording status through read-only endpoints. See docs/PAPER_TRIALS.md for exact commands and limitations.

The local stack initially rejected operator-edited RISK_PER_TRADE=0.05 and MAX_OPEN_POSITIONS=10. Restored the Prompt.md-required limits of 0.005 and 3 in ignored .env, preserving credentials and PAPER/demo mode. PostgreSQL migration/schema check and HTTP smoke checks passed; all five running services are healthy.

Final local verification: 114 backend tests passed with all PostgreSQL cases enabled (none skipped), 7 frontend tests passed, TypeScript/Vite production build passed, Ruff and diff whitespace checks passed. SQLite legacy upgrade preservation and PostgreSQL migration 0005/schema consistency passed. Two existing warnings remain (Starlette HTTPX deprecation and sparse-class legacy synthetic calibration). Browser visual verification remains unavailable.

The initial wall-clock fixture diagnostic recording (`786fcdcc-dfd3-4039-9246-9feb4def1c69`) was later stopped before enabling provider feeds. After an actual trading-worker restart, the same run retained samples, reported two worker instances and a continuity break, and remained fresh. It correctly reports zero healthy/model-observed duration. This short diagnostic is not a real-market soak. The application still has zero paper deployments and zero orders.

Backend milestone committed as `8b8ff20` (audited deployments and persistent recording). Dashboard/operator documentation changes are a separate delivery commit. Secrets, local mode/risk settings, model artifacts and recordings are excluded from Git.

## Dashboard 502 investigation

Observed direct backend `/health/live`, `/health/ready` and `/api/overview` returning HTTP 200 while the same paths through port 5173 returned HTTP 502. Docker reported all services healthy, but the frontend health probe checked only its static root. The backend had restarted more recently than Nginx. Confirmed after approval access recovered: Nginx attempted upstream 172.19.0.2 while the healthy backend was at 172.19.0.3. The running frontend still contained the old proxy configuration.

Prepared a frontend proxy fix using Docker DNS with a five-second cache and variable proxy target, preserving request paths and query strings. Changed frontend health to probe proxied readiness. Added an isolated Docker regression script and CI step that replace the backend with a different IP and require recovery without restarting the proxy. This follows Nginx's documented variable proxy/resolver behavior: https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass and https://nginx.org/en/docs/http/ngx_http_core_module.html#resolver.

Resolved and deployed: dashboard HTTP smoke checks, Nginx syntax, database schema consistency, 7 frontend tests, production build, Ruff and whitespace checks passed. The isolated Docker regression replaced the backend with a different IP and verified health/API paths and query strings recovered without restarting the proxy. No trading settings, orders, database contents or credentials were changed for the proxy fix. Rebuild with `docker compose up --build --no-deps -d frontend`; verify with `.venv/Scripts/python.exe scripts/verify_proxy_recovery.py` and `.venv/Scripts/python.exe scripts/verify_stack.py`.

## Real market display enabled (October 14, 2026 UTC)

Resolved the user's January 2025 chart: ignored local .env now has DEMO_MODE=false with TRADING_MODE=PAPER and live execution disabled. The market worker has fetched current OANDA and Coinbase candles and stored fresh bid/ask quotes for EUR_USD, GBP_USD, BTC-USD and ETH-USD. Both providers reported CONNECTED from actual quote timestamps. The OANDA stream initially timed out and recovered through the existing reconnect loop; a separate bounded diagnostic connection also timed out. This is observed connectivity, not an uninterrupted-feed guarantee.

Live candle polling is bounded to the latest 300 intervals so an old research dataset cannot monopolize the worker by backfilling months before other symbols. Deferred historical gaps are audited; the explicit download command remains the backfill path. System health now derives connection status from each provider's instrument quotes and freshness. The chart shows the completed candle's UTC date/time plus a separate bid/ask timestamp, labels unavailable/stale quotes, and discloses the 15-second dashboard refresh.

Verification: 117 backend tests passed including PostgreSQL cases, 9 frontend tests passed, production build and HTTP smoke checks passed. Proxy recovery was independently verified after changing a stub backend IP without restarting Nginx; its committed fix c936edc passed GitHub run 38590207560. Current market-data changes are a separate delivery commit. A new REAL_MARKET_PAPER recorder run (`830f86ec-8a53-467d-a9c1-f1a65ffbce29`) records infrastructure observations. No model deployment or broker order was authorized. Historical fixtures remain preserved separately from provider data.
