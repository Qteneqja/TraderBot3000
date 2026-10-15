# Trading activation report

October 15, 2026 UTC. Final research snapshot: 17:45:44 UTC; initial read-only operating snapshot: 17:49 UTC; approved application deployment verified at 18:13 UTC. **No model qualifies and autonomous entry execution remains inactive.** Real-money execution remains unsupported/disabled. This work completed a new bounded comparison and repaired notification/diagnostic infrastructure; it did not establish a trading edge.

## Milestones

| Milestone | Status | Actual evidence / remaining requirement |
| --- | --- | --- |
| Corrected strategy | COMPLETE for the six completed batches; BLOCKED for BTC batch completion | Whole-tick target correction freshly evaluated. BTC native child exited -11; incomplete artifact preserved, no automatic retry. |
| Historical data | COMPLETE for research-only coverage audit | Sixteen original provider slices passed the declared 180-day/99% screen. Current live-tail counts are not blanket completeness attestation. Executable historical costs remain unverified. |
| Model training | COMPLETE for 18 candidates; BLOCKED for three BTC planned fits | Six completed three-family batches, two sparse-sample batches failed before fitting, one BTC batch exited without a result after registering logistic. All nine terminal states preserved. |
| Model qualification | BLOCKED | All 18 completed candidates have zero base/stressed validation trades. No passing review. |
| Final future test | NOT STARTED | No passing parent to freeze; no reservation. Requires at least 45 genuinely future days plus the outcome horizon after freezing. |
| Paper activation | BLOCKED | No eligible model/review; explicit operator approval remains required once evidence exists. |
| Paper execution | IMPLEMENTED — AWAITING VERIFICATION on qualified provider opportunities | Deterministic fixture-only SQLite/PostgreSQL fill/exit/P&L/outbox lifecycle passed with mocked model authority. Zero real-market paper orders. Durable market entries are supported; runtime pending limit/stop execution remains unsupported. |
| OANDA integration | IMPLEMENTED — AWAITING VERIFICATION of external lifecycle | Fresh read-only acceptance and reconciliation pass; mock/fault suite passes. Actual fill/protection/close/restart lifecycle unverified. |
| Telegram | COMPLETE for one approved connection test; IMPLEMENTED — AWAITING VERIFICATION for actual trades | One confirmed API receipt after bot/chat checks. Future confirmed lifecycle delivery enabled. No actual fill/close message exists because no trade exists. Full operational-alert catalog remains incomplete. |
| Practice execution | BLOCKED | Qualified model, completed formal paper trial, cost review and separate practice-test authorization precede any demo order. No authorization/order exists. |
| Continuous operation | IMPLEMENTED — AWAITING VERIFICATION of sustained continuity | Docker services run with restart policies; all four worker heartbeats and all four provider quotes fresh at final observation. Host sleep/restarts/clock gaps prevent claiming uninterrupted or permanent deployment. |
| Failure recovery | COMPLETE for automated software cases; IMPLEMENTED — AWAITING VERIFICATION externally | 262 backend tests passed with PostgreSQL enabled, zero skipped; actual broker restart with owned exposure and sustained soak not yet performed. Native BTC root cause remains unresolved. |

## A. Root cause

The first legitimate order is blocked by the absence of a qualified, explicitly active PAPER model, not by a stopped worker or a disconnected feed. Strategies are implemented hypotheses. Earlier artifacts cannot be reclassified after the precision correction. Fresh validation target probabilities remain below .80; model training and LLM commentary cannot authorize a trade. Additional spread, entry-drift and stale-quote rejections are legitimate deterministic checks. Historical fixture/precision rejections remain immutable.

This session implemented strict Telegram receipts, interrupted-send quarantine, fenced completion, bounded rate-limit deadlines, richer authoritative trade messages, a safe one-test command, migration 0010, read-only activation diagnostics, worker evaluation counters, and the fixture execution/notification acceptance test. It corrected the invalid Telegram destination through approved metadata lookup. Native BTC failure exposed missing crash evidence; isolated future research-child tracing now captures fatal stack locations without local values. That instrumentation does not identify or repair the old native root cause and does not retry the batch.

## B. Historical data

The audited provider dataset below is separate from the 32,000 labeled fixture candles. All rows have RESEARCH_ONLY status, not execution qualification. Audits end exclusively at 2026-10-14 00:00 UTC. FX 1m/5m/15m start 2025-10-14; FX 1h start 2024-10-14. Crypto 1m/15m start 2026-04-14; crypto 5m/1h start 2025-10-14. A small older isolated BTC sample is excluded from these audited slices and from the bounded new fits.

| Asset | Timeframe | Audited candles | Usable days | Session coverage | Unexplained missing |
| --- | ---: | ---: | ---: | ---: | ---: |
| EUR_USD | 1m | 370662 | 311 | 99.6629% | 1252 |
| EUR_USD | 5m | 74589 | 259 | 99.9960% | 3 |
| EUR_USD | 15m | 24864 | 259 | 100% | 0 |
| EUR_USD | 1h | 12432 | 302 | 99.6154% | 48 |
| GBP_USD | 1m | 371043 | 311 | 99.7641% | 876 |
| GBP_USD | 5m | 74577 | 259 | 99.9798% | 15 |
| GBP_USD | 15m | 24863 | 259 | 99.9960% | 1 |
| GBP_USD | 1h | 12432 | 302 | 99.6154% | 48 |
| BTC-USD | 1m | 263089 | 183 | 99.8364% | 431 |
| BTC-USD | 5m | 104971 | 365 | 99.8583% | 149 |
| BTC-USD | 15m | 17543 | 183 | 99.8577% | 25 |
| BTC-USD | 1h | 8750 | 359 | 99.8858% | 10 |
| ETH-USD | 1m | 263082 | 183 | 99.8338% | 438 |
| ETH-USD | 5m | 104971 | 365 | 99.8583% | 149 |
| ETH-USD | 15m | 17543 | 183 | 99.8577% | 25 |
| ETH-USD | 1h | 8750 | 359 | 99.8858% | 10 |

Total: 1,754,161 audited provider candles. Original hashes are in ignored `data/reports/canada-v1-provider-coverage-summary-20261014.json`. OANDA Canada session handling includes NY DST/daily breaks and verified Christmas/New Year overrides; other historical closure gaps remain unexplained. No bars were fabricated. Fresh campaign five-minute slices were rechecked independently through exclusive 2026-10-15 00:00 UTC. All completed candidate slice coverage checks pass; exact manifests are in the qualification report. Coverage alone does not establish predictive samples or profitability.

## C. Model training

Campaign `activation-corrected-20261015-v1` predeclared nine batches and 27 planned fits. Logistic, LightGBM and XGBoost completed for EUR_USD trend/momentum/breakout/structure, GBP_USD trend and ETH-USD trend: 18 candidates, all zero validation trades at .80, including doubled costs. EUR mean reversion had only 261 filled candidates and volatility only 282 against the minimum 300 before purging; six planned fits did not proceed. BTC's native child exited -11 after registering its logistic artifact; no completed batch result exists. Its remaining fits are incomplete/unverified. No failed/UNKNOWN run was reset or blindly retried.

All completed probability histograms are below .40, far below the required .80; this is measured abstention, not a hidden execution switch. Some Brier scores beat the class-frequency baseline, but that does not satisfy the activity/economic gates. Sparse breakout/structure calibration partitions also lack the required 200 calibration samples. Full model IDs, artifact hashes, sample counts, input/partition dates, base/stressed metrics and exact failures are in [FINAL_MODEL_QUALIFICATION_REPORT.md](FINAL_MODEL_QUALIFICATION_REPORT.md). Undefined profit factor/expectancy is not a passing zero-risk strategy.

Nine campaign-only schedules were disabled after the last job was claimed to prevent annual repetitions. Original twelve weekly candidate-only schedules remain enabled. Repeated fitting of identical hypotheses is not itself a strategy improvement; new horizon/features/regime/cost hypotheses must be justified and predeclared rather than tuned to a final test.

## D. Final model validation

NOT STARTED / NOT PASSED. No eligible frozen parent or future reservation exists. The policy requires a disjoint prospective period at least 45 days long plus the complete 12-bar outcome horizon. No exact completion date can be promised before a passing candidate is frozen. Previously inspected history cannot be reused as newly untouched evidence. Reservation/finalization is implemented and tested with clearly mocked positive orchestration; no actual future period has elapsed under a reservation.

## E. Model activation

No model is active in PAPER or OANDA_PRACTICE. For a genuinely passing future-evaluated candidate, the operator must inspect the exact model/review/artifact/cost evidence and explicitly approve this local command:

```powershell
docker compose exec backend python -m app.cli activate-paper QUALIFIED_VERSION --review PASSING_REVIEW_ID --operator local-operator --reason "Explicit approval of reviewed PAPER candidate"
```

These are unavailable placeholders, not executable current identifiers. Training never invokes activation. Formal trial policy approval and start are separate; see [PAPER_TRIALS.md](PAPER_TRIALS.md). No account suspension was lifted.

## F. Paper trading

Actual provider-generated paper orders: **0**. Completed trades: **0**. Open positions: **0**. Pending orders: **0**. No trading return or win rate has been observed; recorded realized trading P&L is zero because no trade occurred. The infrastructure recorder is not a completed formal performance trial. At 17:49 UTC the trading worker evaluated four instruments, observed three candidate attempts in its last cycle and had no missing quotes. Fixtures tested the fill/exit/ledger/notification path only and were not inserted into the production ledger.

## G. OANDA practice

Fresh read-only checks passed at approximately 17:15 UTC: configured practice account, CAD/non-MT4, positive NAV/free margin, supported precision/units/margin, fresh tradeable quotes, flat exposure and stable transaction access. Reconciliation at cursor 810 had no discrepancies. Entry submission remains disabled and the practice account remains suspended. Broker-confirmed strategy orders: **0**; no order ID/protective fill/restart-with-exposure evidence exists.

The adapter's market FOK/OPEN_ONLY, signed units, price bound, native stop/target-on-fill and MT4 restriction were compared with current official [order definitions](https://developer.oanda.com/rest-live-v20/order-df/) and [order endpoints](https://developer.oanda.com/rest-live-v20/order-ep/). This schema review does not prove external fills. Follow [BROKER_INTEGRATION.md](BROKER_INTEGRATION.md): qualified PAPER model and completed formal trial, reviewed costs, fresh reconciliation, explicit one-unit test approval, actual protected fill/close/notification/restart verification, then a separate autonomous authorization. No demonstration bypass exists. Pending broker limit/stop orders and crypto execution remain unsupported.

## H. Telegram

Bot authentication and chat verification succeeded after correcting the recipient; exactly one explicitly approved connection test was API-confirmed DELIVERED around 17:25 UTC. Initial HTTP 400/chat-not-found failure remains recorded. The verified private numeric destination and credentials remain ignored. Automatic future confirmed lifecycle delivery is enabled; the outbox has one delivered test and no actual trading notifications. Mock lifecycle tests prove durable entry/exit events and receipt handling, not actual trade delivery. See [TELEGRAM.md](TELEGRAM.md) for retry/quarantine behavior and remaining alert-catalog limitations.

## I. Operational readiness

| Environment | Current readiness |
| --- | --- |
| PAPER | Infrastructure runs and abstains correctly; entry activation BLOCKED by model/final evidence. |
| OANDA_PRACTICE | Read-only checks pass; external strategy execution BLOCKED by qualification/trial/broker authorizations and actual lifecycle evidence. |
| LIVE | UNSUPPORTED and disabled. |

All seven Compose services were healthy during verification. Four worker heartbeats and all four matching-provider quotes were fresh at 17:49 UTC. Docker restart policies and persistent volumes support continuing local operation; the computer/Docker must remain running. This is not a claim of permanent hosting, uninterrupted observation or a completed sustained soak.

Verification: **262 backend tests passed**, PostgreSQL enabled, no skips; **21 frontend tests** and production build passed. Ruff/diff checks passed; SQLite legacy-order/notification preservation and PostgreSQL upgrade/schema check passed. HTTP/proxy smoke passed. The two existing Starlette HTTPX/sparse-class warnings remain. [Implementation CI 38778978068](https://github.com/Qteneqja/TraderBot3000/actions/runs/38778978068) passed for `7461adf`. [Final revision CI 38781047692](https://github.com/Qteneqja/TraderBot3000/actions/runs/38781047692) also passed both jobs for `cf51339`, including the crash-trace test, PostgreSQL migrations and frontend proxy recovery. Browser visual verification was not performed.

An earlier rebuild request was declined; the user subsequently explicitly approved deployment of cf51339. The current workspace differed only in two documentation files. Rebuilt backend, frontend, trading-worker and learning-worker with that unchanged application source. At 18:13 UTC all seven services were healthy, all four worker heartbeats fresh, schema consistency/HTTP proxy smoke passed, provider-separated diagnostic fields present and native-crash tracing installed in the learning worker. No queued/running research job was interrupted. Recorded deployment audit evidence; PAPER/live=false/zero active model deployments/zero paper or practice orders and the single earlier Telegram receipt were preserved. The complete suites were not rerun for this source-unchanged deployment; prior 262/21-test verification and successful cf51339 CI remain applicable. No rebuild occurred before the subsequent explicit approval.

## J. Remaining work and operating commands

1. Diagnose the native BTC failure using preserved evidence and a separately declared instrumented attempt; do not reset or blindly replay its failed run. Crash tracing is installed for future CLI children; it does not retrospectively diagnose or repair the past failure.
2. Research a defensible candidate that meets unchanged sample, calibration, activity, economic, risk and cost-stress requirements. The current completed candidates fail; activation cannot manufacture evidence.
3. After passing selection and independent cost/regime/portfolio review, freeze/reserve a new prospective test and collect at least 45 future days plus the outcome horizon. Evaluate once without refitting.
4. Explicitly activate a fully qualifying PAPER model, approve/start its formal trial and observe the required elapsed time and outcomes. Only genuine qualified opportunities may create orders.
5. Complete separately approved OANDA practice fill/protection/close/restart/notification acceptance before autonomous practice authorization.
6. Complete unsupported pending-order/partial-exit workflows and the requested broader operational-alert/daily-summary catalog under separately validated execution semantics. Current implementation must not be labeled complete for those features.
The previously pending application deployment is complete after explicit approval and runtime verification; it is no longer a remaining blocker. Model qualification and external lifecycle requirements above still apply.

Safe read-only operation now:

```powershell
docker compose ps
docker compose exec backend python -m app.cli activation-diagnostic
docker compose exec backend python -m app.cli research-campaign-report activation-corrected-20261015-v1 --output data/reports/NEW-UNIQUE.json
docker compose exec backend python -m app.cli practice-reconcile
.venv/Scripts/python.exe scripts/verify_stack.py
```

For future authorized restarts/deployments, existing Compose definitions preserve data and credentials. Check that no active research job will be interrupted:

```powershell
docker compose up --build -d
docker compose exec backend alembic check
.venv/Scripts/python.exe scripts/verify_stack.py
```

Do not seed fixtures into provider qualification, delete volumes, weaken thresholds, mark test mocks as approval, use an LLM narrative as execution authority, or submit an order merely to demonstrate activity.
