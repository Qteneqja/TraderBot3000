# Operations

Follow README for startup. Apply migrations, bootstrap, then start API/workers. Liveness checks process availability; readiness checks database, migration revision and initialized account. Feed health depends on quote age and worker events.

The market worker streams quotes and REST-refreshes candles. Paper worker reconciles before monitoring/evaluation. Demo mode never pretends historical fixtures are current quotes. Runtime can observe explicitly deployed SHADOW models, but those models cannot approve execution. Explicit account-scoped paper trials and a persistent recorder are available through the local CLI; see [PAPER_TRIALS.md](PAPER_TRIALS.md). No current model qualifies.

Workers write heartbeat/failure events to the audit table. Failures log exception types, avoiding credential-bearing URLs. Retention, restart alerts, notification dispatch, broker transaction monitoring and drift alerts remain outstanding.

Recovery: suspend new entries, inspect failure/quote timestamps, verify order/account state, resolve unknown outcomes, then restart through reconciliation. Never delete orders or volumes as a shortcut. Local services stop with Ctrl+C; Compose stops with `docker compose stop`.

Troubleshooting:

- Empty chart: check DEMO_MODE/source, seed fixtures or download provider history.
- Dashboard 502 while port 8000 is healthy: check the frontend proxy. Its backend hostname must be resolved through Docker DNS after backend replacement. Rebuild the frontend with `docker compose up --build --no-deps -d frontend` to install the current proxy configuration. The frontend health check now verifies proxied `/health/ready`, so a working static page alone cannot report a healthy dashboard.
- No trades: expected without execution-validated inference; inspect rejection reasons.
- Missing OANDA key: configure practice credentials; public crypto analysis is independent.
- Readiness 503: run migrations and `python -m app.cli init`.
- Admin disabled: configure ADMIN_TOKEN; normal dashboard reads remain local.
- Windows runtime/Vite permission errors: sandbox approval may be needed; `npm.cmd` only fixes PowerShell's npm script restriction.
- Existing model artifact: preserve it, create a deliberate new experiment directory and do not reuse the test set for tuning.
- Model candle manifest mismatch: restore the original dataset or start a new experiment; do not rewrite the registered hash to pass verification.
- Paper position lacks cost metadata after upgrade: reconciliation suspends it. Preserve the order and investigate; migration never fabricates historical charges.

Current schema is migration `0005`, including research reviews, paper deployment history/current slots and recorder runs/samples. Docker's migration job applies upgrades before API/workers start. The SQLite upgrade test preserves an older open order and confirms it is quarantined when its original cost assumptions are unavailable. PostgreSQL schema consistency was also checked after upgrade.

Research example and shadow commands are in README. Model artifacts and JSON reports stay in named volumes and are excluded from Git. The Model lab displays stored probabilities and distinguishes replay from streaming. Reports are immutable; choose a new output filename for a new evaluation.

Assessment results appear under Acceptance reviews in Model lab. `REJECTED` includes unmet criteria; `RESEARCH_GATES_PASSED` still does not activate trading. Do not weaken policy values to make the synthetic demonstration pass. New policy versions require new experiments and separately justified validation research.

Future AWS design: private EC2 or small ECS deployment, encrypted managed PostgreSQL/backups, Secrets Manager, CloudWatch, TLS and authenticated ingress. Keep one execution owner per account until leasing is proven. Restore tests and long paper/practice soak tests must precede live consideration. No AWS deployment is performed.

## Current provider data versus fixtures

DEMO_MODE=true deliberately selects synthetic historical candles; it cannot provide live prices. For provider data, set DEMO_MODE=false in ignored .env while retaining TRADING_MODE=PAPER and ENABLE_LIVE_TRADING=false, then recreate services with `docker compose up --build -d`. This enables market-data streams/polling, not broker orders. Stop any fixture recorder run before starting a real-market recording.

The dashboard presents completed candles separately from latest bid/ask quotes and refreshes every 15 seconds. A five-minute candle appears only after it closes and the next ingestion poll completes. System health reports CONNECTED only while every configured instrument for that provider has a fresh matching-source quote, DEGRADED for partial freshness, and WAITING_FOR_FRESH_QUOTES otherwise. Initial connection failures and later outages are recorded and retried; configured credentials alone are not proof of current connectivity.

The live polling loop fetches at most 300 recent intervals per symbol/timeframe on each cycle. If existing history is older, an audited market_history_gap_deferred event identifies the skipped interval. Use the explicit download command to fill older research gaps; no candles are fabricated and recent polling does not imply a complete training dataset.
