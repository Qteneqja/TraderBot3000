# Controlled learning

October 15 continuation: eight additional weekly momentum/mean-reversion plans are running/queued across the four provider assets and four CPU families (thirty-two planned candidate fits). Original trend schedules remain. A stale first-job lease was quarantined rather than retried; training continues with other independent plans. Strategy names now distinguish same-asset schedules in Model lab. [DeepSeek commentary](LLM_INTEGRATION.md) is implemented separately, offline pending explicit external-sharing approval; it never supplies labels or promotes models.

Migration 0007 adds immutable attributed outcomes, explicit research schedules and claimable jobs. The separate learning-worker collects closed outcomes, monitors deployed models and trains candidates without blocking market/execution workers. It cannot activate, replace or roll back models.

## Outcomes and drift

Outcomes retain authoritative original probabilities, model/artifact/deployment association, regime/strategy, entry/exit, holding duration, costs, net P&L and risk-relative results. PAPER, OANDA_PRACTICE, fixture diagnostics and quarantined records stay separate. Practice monitoring requires an account fingerprint so accounts/currencies cannot be pooled. Checksums detect changed outcome evidence. Executed trades are a selected sample: they are monitoring evidence, not duplicated as independent supervised training rows. Training derives causal labels from completed provider candles.

Monitoring reports rolling P&L, profit factor, win rate, realized trade-sequence drawdown, calibration/Brier evidence, regime breakdowns and train-referenced feature/probability shifts. Feature shifts alone are warnings. Outcome deterioration requires two consecutive nonoverlapping windows of 200 labeled outcomes, both with target-success Wilson upper bounds below predicted probability minus .05 and Brier deterioration over .05. Fewer outcomes are insufficient. These intervals do not remove serial dependence or fill-selection bias; diagnostic drawdown is not continuous account drawdown.

Automatic suspension defaults off. Both ENABLE_DRIFT_SUSPENSION=true and explicit drift-policy-approve audit approval are required. Before mutation, the worker recomputes the report under the account lock and verifies the current deployment. Suspension stops entries and queues an alert; existing-position management continues. No model switches occur.

```powershell
docker compose exec backend python -m app.cli collect-outcomes
docker compose exec backend python -m app.cli model-monitor VERSION --mode PAPER
```

## Scheduled research

Plans fix provider/symbol, five-minute timeframe, strategy, 180-1095 history days, 7-365 day interval, families and explicit Decimal spread/slippage/fee/financing assumptions with provenance. Only validation-only jobs are accepted. CPU families: logistic, random_forest, lightgbm, xgboost. Schedules require local operator attribution; that label is not authenticated multi-user identity. Restrict shell/database/artifact access.

```powershell
docker compose exec backend python -m app.cli learning-enable data/reports/PLAN.json --first-due FUTURE_ISO_UTC --operator local-operator --reason "Predeclared comparison"
docker compose exec backend python -m app.cli learning-tick
docker compose exec backend python -m app.cli learning-disable SCHEDULE_ID --operator local-operator --reason "Pause research"
```

The worker refreshes completed history, verifies coverage, fits training-only transforms, purges overlapping labels, calibrates independently and records three expanding walk-forward folds before the sealed final partition. It registers EXPERIMENTAL artifacts and evaluates validation portfolios and doubled costs. Family-specific failures remain visible. Same-scope incumbents can be compared on candidate validation periods with shared costs, original feature context and cutoff checks; incompatible scopes, changed artifacts and sealed periods are rejected. No active model currently exists for an actual incumbent comparison; that orchestration is mocked in tests.

Atomic claims prevent duplicate jobs. Missed intervals coalesce. Parent heartbeats remain independent of slow fitting. Lost leases become UNKNOWN without automatic retry; stale children cannot overwrite quarantine or publish another model after losing their lease. Orphan artifact files may need manual reconciliation. Neither a crash nor an orphan artifact grants authority. Failed schedules remain enabled for their next independently dated weekly run; disable explicitly when investigation is needed.

## Final evidence and promotion

Scheduled jobs never calculate final-test model scores, class-baseline scores or portfolio results. Direct backtest-model --partition test rejects validation-only artifacts too. Assessment requires FULL final evidence, current policy, verified coverage, all walk-forward folds and every original economic/calibration/risk requirement. Artifacts bind feature/strategy/risk/replay implementations; source changes invalidate old deployment evidence.

Earlier full-test experiments already inspected October 2025-October 2026. Further comparisons on that history are selection research and cannot call it newly untouched. Migration 0008 implements explicit prospective reservation/finalization for a selected frozen candidate. Validation-only artifacts still cannot activate. Genuine passing final evidence must use the separate explicit PAPER activation/rollback path.

The reserve-final-test command requires every current validation portfolio/calibration/baseline/uncertainty/doubled-cost gate, sufficient provider history/calibration and all walk-forward folds. It fixes a strictly future, timeframe-aligned period of at least 45 days, exact parent metadata/artifact, training-only class-frequency baseline, current policy, operator attribution and evaluation/dependency implementation hashes. One reservation per parent; overlapping context/outcome periods across models in the same symbol/provider are prohibited. A failed or abandoned reservation is never moved, deleted or reused as another final test.

Scheduled and CLI training stop before pending reserved periods, including cross-timeframe same-symbol research. After consumption/abandonment, past data may train later candidates, whose final periods must be new and disjoint. This does not make old final metrics selection evidence for the frozen parent. Raw market collection/chart access remains possible; these application checks do not prevent a privileged operator from inspecting data or directly editing the database/artifacts. Preserve the preregistered plan and trust boundary.

```powershell
# Only for an actually passing frozen candidate; the current sixteen models do not qualify.
docker compose exec backend python -m app.cli reserve-final-test VERSION --start FUTURE_START_ISO_UTC --end FUTURE_END_ISO_UTC --operator local-operator --reason "Freeze candidate for untouched final evaluation"
# Only after the end plus the full outcome horizon has elapsed:
docker compose exec backend python -m app.cli evaluate-final-test RESERVATION_ID
# Explicit permanent abandonment, including after an interrupted process:
docker compose exec backend python -m app.cli abandon-final-test RESERVATION_ID --operator local-operator --reason "Document incident and permanently abandon this final period"
```

Evaluation commits a one-shot EVALUATING claim before reading future outcomes. It verifies original input candles, both overall and future-slice completeness, frozen parent integrity and at least 100 final candidates, predicts with the existing estimator without fitting/calibration, writes a new exclusive immutable artifact and runs the unchanged full assessment. The artifact links its exact parent and reservation. It remains EXPERIMENTAL even if research gates pass. Activation rechecks completed reservation provenance; an in-progress receipt cannot activate. Exceptions consume the attempt as FAILED. A crashed EVALUATING claim needs explicit abandonment/review; there is no blind retry. Abandoned workers cannot overwrite the operator's decision or activate stale results. Orphan files/reviews require manual investigation, not deletion/retry to seek better outcomes. Model lab exposes bounded read-only final-evaluation statuses, including rejected assessments.

October 15 actual result: all sixteen scheduled models completed, with zero validation trades under both original and doubled costs at the unchanged 80% threshold. No future test was reserved or evaluated. Positive future-evaluation orchestration tests mock selection evidence, coverage and labels explicitly; they are software tests, not a qualifying strategy or elapsed future evidence.

Actual October 14 operation: weekly trend research scheduled for all four symbols and all four families. FX spreads use the first week's observed median close spread (.00016 EUR, .00019 GBP), one-tick slippage and explicitly unverified zero fee/financing simulation assumptions. Crypto uses an assumed two-basis-point full spread from the first-week median close (21.89 BTC, .79 ETH), one-tick slippage and **1.2% taker fee per side**, with no maker discount. These are conservative research assumptions, not verified account charges or observed crypto spreads. The user elected an assumed fee rather than supplying actual rates. [Coinbase states actual fees depend on product, tier and order type](https://help.coinbase.com/en-gb/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees); verify actual costs before execution-quality qualification. Crypto execution remains unsupported.

Read-only /api/learning and Model lab show schedules, recent states, validation summaries and outcome classifications. No HTTP authority-changing endpoint exists. Notifications are durably queued for model-bound PAPER fills/closes, practice events and approved drift suspension. Atomic claims prevent concurrent duplicate sends; ambiguous Telegram timeouts become UNKNOWN without blind retries. ENABLE_NOTIFICATIONS defaults false. Actual delivery has not been enabled or verified locally.
