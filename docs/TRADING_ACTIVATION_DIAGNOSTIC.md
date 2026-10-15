# Trading activation diagnostic

Assessment: October 15, 2026 UTC. This report distinguishes software tests, current provider observations, research failures and unverified execution. See [activation report](TRADING_ACTIVATION_REPORT.md) and [final qualification](FINAL_MODEL_QUALIFICATION_REPORT.md) for the session's final checkpoint.

| Question | Observed answer and responsible component |
| --- | --- |
| Real historical data available? | Yes. Sixteen provider series passed the previous research-only duration/session audit; see `docs/HISTORICAL_DATA.md` and the ignored `canada-v1-provider-coverage-summary-20261014.json`. Fixtures are separate sources. Live tail counts are not a new completeness audit. `market_data/coverage.py:coverage_report` checks the specific training slice again. |
| Corrected strategy implemented? | Yes. `strategies/registry.py:candidates_from_row` rounds the 2.5R reward outward to whole instrument ticks. Twelve regression cases cover directions, odd/even distances and multiple tick sizes. No precision gate was relaxed. |
| Freshly evaluated? | A new predeclared 27-fit campaign uses the corrected strategy and notification-integrated execution source contract. Completed results and remaining failures are documented in the qualification report; no prior artifact was relabeled. |
| Model passes acceptance? | No passing model has been demonstrated. Completed fresh candidates produce zero validation trades at the unchanged 80% threshold; zero trades cannot satisfy the 100-trade, active-day, profitability, profit-factor or uncertainty requirements. Sparse strategies fail before fitting. `machine_learning/policy.py:acceptance_policy`, `assessment.py:partition_checks`. |
| Untouched chronological test available? | New artifacts seal their historical test partition, but historical periods have already informed earlier research. They cannot replace a genuinely new final observation period. `prospective.py:reserve_period/evaluate_period` require a passing frozen candidate and a disjoint future period of at least 45 days, plus its outcome horizon. No reservation exists. |
| Model approved and active? | No. Zero current `PaperDeploymentSlot` entries and zero passing deployment reviews. `machine_learning/deployment.py:validate_evidence/activate` fail closed; registry EXPERIMENTAL/SHADOW flags confer no execution authority. |
| Market-data service operational? | At the 17:28 UTC observation, its heartbeat and matching-source quotes for EUR_USD, GBP_USD, BTC-USD and ETH-USD were fresh. `worker.py:market_worker`, `market_data/providers.py`. This does not establish uninterrupted uptime. |
| Trading worker operational? | Yes at that observation. Its last recorded cycle evaluated four instruments, observed three candidates and lacked no quotes. `worker.py:trading_worker`; Docker restart policy is configured. Host sleep/clock gaps still interrupt continuous observation. |
| Candidates generated? | Yes. At that observation 393 unique stored decisions existed, including historical fixtures, and the latest provider decision was 17:25 UTC. Evaluation attempts and unique signals are distinct. The new diagnostic separates provider samples from legacy fixture totals. |
| Why rejected? | Every stored decision then lacked a validated calibrated model. Additional historical reasons included entry drift, spread/reward budget, stale quotes and the earlier precision defect. Some retained decisions predate the fix; they must not be rewritten. `execution/paper.py:submit`, `risk_management/engine.py:approve`. |
| Paper engine can create orders? | Fixture-only SQLite/PostgreSQL tests verify fill, valid protective levels, duplicate suppression, exit, exact net P&L and ledger updates, plus notification events. Positive model authority is explicitly mocked. This is software evidence, not a qualified real-market order. `tests/test_activation_lifecycle.py`, `tests/test_execution.py`, `tests/test_paper_faults.py`. |
| OANDA authentication working? | Yes in fresh read-only checks at approximately 17:15 UTC: CAD/non-MT4 practice account, precision, conversions, margin, tradeable prices and flat exposure. Reconciliation cursor 810, no discrepancies; submission remains false. `brokers/validation.py:readiness_report`, `brokers/reconciliation.py:reconcile_practice`. |
| Broker acceptance incomplete? | Qualified PAPER model, execution-quality/cost evidence, completed formal paper trial, explicit one-unit test authorization, actual protected fill/close/restart verification and separate autonomous authorization. Mock tests cannot satisfy external lifecycle evidence. `docs/BROKER_INTEGRATION.md`. Pending broker limit/stop entries and crypto execution remain unsupported. |
| Telegram delivers? | One explicitly approved connectivity message was API-confirmed after bot authentication and chat verification. The initial name was not a valid chat ID; approved metadata lookup identified one recent private destination. Ignored configuration now uses that numeric ID. Automatic lifecycle delivery is enabled, but no actual trading notification exists because there are no trades. `notifications/telegram.py`, `notifications/messages.py`. |
| First legitimate trade blocked by? | The missing qualified, explicitly activated model. Healthy workers, a connection-test receipt and fixture trades cannot replace model acceptance. Practice has the additional broker gates above. |

## What was repaired

The previous precision fix is retained. This session adds complete recorded PAPER fill/closure facts and richer practice messages, strict Telegram delivery receipts, safe error codes, rate-limit deadlines, interrupted-send quarantine, claim fencing and a single-message connectivity command. Migration 0010 preserves legacy evidence without inventing delivery timestamps. Read-only activation diagnostics, worker evaluation counters and dashboard visibility make zero-order behavior inspectable.

The final source also separates provider rejection samples from legacy fixture totals and records delivery time after the API response. The last rebuild request was declined; these final refinements are tested/committed but not installed in the running containers. Earlier receipt/diagnostic functionality is deployed. No rebuild was retried to circumvent that decision.

## Inspect current evidence

```powershell
docker compose exec backend python -m app.cli activation-diagnostic
docker compose exec backend python -m app.cli research-campaign-report activation-corrected-20261015-v1 --output data/reports/campaign-NEW-UNIQUE.json
docker compose exec backend python -m app.cli practice-check --output data/reports/practice-NEW-UNIQUE.json
docker compose exec backend python -m app.cli practice-reconcile
```

Reports are immutable; select a new filename for each observation. Never print `.env`, raw broker responses or Telegram message contents. The diagnostic is read-only and cannot approve models, lift suspension or authorize orders.
