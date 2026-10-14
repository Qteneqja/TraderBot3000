# Paper model trials and operational recording

Paper activation is an explicit local operator action. It authorizes simulated entries for the PAPER account only after a content-verified `RESEARCH_GATES_PASSED` review. It does not establish a trading advantage, approve practice/live execution, or waive independent regime and execution-quality validation. The current fixture models remain ineligible. Training and assessment never activate anything.

## Deployment contract

Migration 0005 adds immutable deployment history and one current slot per account/source/symbol/strategy/timeframe. Account locking serializes deployment changes with order submission on SQLite and PostgreSQL. Repeated activation of the same current contract is idempotent. Replacement and rollback append history; they do not rewrite research artifacts or registry status. A repeated rollback to the already restored target is idempotent.

Activation verifies the artifact checksum and embedded metadata, the review content hash and all required checks, policy/risk settings, original stored candle manifest, and runtime instrument/cost settings. History must precede activation. Initial support is the existing 5-minute, 12-bar, USD-quoted paper workflow. Spread must be positive in the reviewed assumptions; each runtime spread must be no greater. Slippage, fee and financing settings must match the reviewed model. These are modeled costs, not verified broker charges.

Every new submission rechecks current deployment, artifact, review and configuration under the account lock, reconstructs the candidate from stored completed candles, and computes model probabilities itself. Caller-supplied probabilities, features and protective levels cannot authorize execution. The independent risk engine can still reject any inferred candidate. The signal records its actual probability and deployment; filled orders retain the deployment and original cost contract. A legacy registry `ACTIVE` flag or `execution_validated` field grants no authority.

Rollback revalidates the target against current evidence/configuration and the stored training manifest. Invalid targets leave the current slot unchanged. Deactivation blocks new entries; it never closes existing positions or disables their monitoring. Account suspension is preserved through all deployment actions. There is no automatic unsuspend operation.

## Operator commands

Run these from the repository root. VERSION, REVIEW_ID and DEPLOYMENT_ID are placeholders from the API/dashboard/CLI, not usable identifiers. Activation requires `TRADING_MODE=PAPER`, `DEMO_MODE=false`, a reconciled unsuspended account, and an eligible real-market model. Do not switch modes to bypass a failed review.

```powershell
docker compose exec backend python -m app.cli activate-paper VERSION --review REVIEW_ID --operator local-operator --reason "Begin supervised paper trial"
docker compose exec backend python -m app.cli rollback-paper DEPLOYMENT_ID --operator local-operator --reason "Restore prior reviewed model"
docker compose exec backend python -m app.cli deactivate-paper DEPLOYMENT_ID --operator local-operator --reason "Stop new entries for this scope"
```

The operator field is an audit label supplied by a trusted local CLI user, not authenticated multi-user identity. There is no deployment write endpoint. Restrict access to the local shell, database and artifact directory. JSON hashes detect changed evidence; they are not signatures protecting against a privileged database/artifact editor.

## Recording

The recorder measures worker activity independently of model eligibility. Start it explicitly for the instruments whose feeds you intend to observe:

```powershell
docker compose exec backend python -m app.cli paper-record-start --symbols EUR_USD GBP_USD BTC-USD ETH-USD
docker compose exec backend python -m app.cli paper-record-report RUN_ID
docker compose exec backend python -m app.cli paper-record-stop RUN_ID
```

Only one run can be open for the PAPER account. Starting the same configuration returns the existing run; configuration changes require stopping it and starting another. Workers resume the open run after a restart without resetting history. No recorder command changes DEMO_MODE, activates a model, sends a notification, or submits a broker order.

Each approximately ten-second worker cycle persists a deduplicated sample with UTC and monotonic timestamps, worker identity, feed ages/provenance, deployment IDs, configuration hash, equity timestamp, account balance/equity, reserved risk, positions, cumulative account fees and realized P&L, and error classifications. Account totals include activity predating the run; they are not isolated trial returns. Samples are committed separately from order transactions. A recorder failure cannot roll back an already committed order; missing observations appear as gaps/staleness.

Healthy duration is credited only between consecutive healthy samples from the same worker, with unchanged deployments and matching wall/monotonic intervals no greater than 30 seconds. Restarts, skipped cycles, clock discrepancies, stale/wrong-source quotes, worker errors, suspended/unreconciled accounts and changed configuration earn no healthy time. Active deployments must still pass evidence checks, belong to recorded feed scopes, and have fresh completed candles. Model-observed duration additionally requires a current paper deployment. A quote-only recording without models is infrastructure evidence only. No model trades are fabricated to improve the counters.

Fixture runs are labeled `FIXTURE_DIAGNOSTIC` and earn zero healthy/model-observed time. Market closures are presently reported as feed gaps; session/calendar classification remains unfinished. Sampled health does not prove uninterrupted availability between polls. Deployment changes remain visible in individual samples and break continuity; a run spanning several deployments is not proof that any single model completed a trial. There is no automatic duration threshold, soak acceptance, or broker promotion.

Model lab and System health show read-only trials and recorder summaries. `/api/paper-deployments`, `/api/paper-runs`, and `/api/paper-runs/RUN_ID/samples` expose history; the samples endpoint returns the latest 100. Summary calculations use database aggregates rather than loading the full run into memory. Long-term retention/export and external outage alerts remain outstanding. Preserve the database volume; do not delete evidence to reset poor results.

## Verification boundaries

Tests exercise activation/replacement/rollback, concurrent activation, tampered reviews/artifacts, configuration drift, caller-confidence forgery, deactivation with an open position, recorder restart/gap/clock behavior, idempotency and commit failures on SQLite and PostgreSQL. Positive research evidence in orchestration tests is explicitly mocked. A separate test uses a real synthetic trained artifact and stored causal features while mocking only prior eligibility. None of these tests demonstrates a qualifying real-market model or a sustained real-time paper trial.
