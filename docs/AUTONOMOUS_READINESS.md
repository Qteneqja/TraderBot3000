# Remaining autonomous milestones: October 14, 2026 UTC

October 15 continuation: schema 0008 prospective reservation/finalization is implemented and tested; all sixteen four-asset/four-family jobs completed with zero qualifying validation trades under base and doubled costs. No final period can be reserved yet. See [actual results and failed gates](RESEARCH_RESULTS.md) and [the one-shot workflow](CONTROLLED_LEARNING.md). Current verification: 211 backend tests, 17 frontend tests, production build, Ruff, PostgreSQL schema check and HTTP smoke passed. No model/order was activated. Older measured checkpoints below remain historical evidence.

## Verified research milestone

The CLI now accepts explicit inclusive `--start` and exclusive `--end` for
`train-candidates`. The new `data-report` command generates immutable reports with
manifest, usable days/windows, duplicate/future checks, session estimates, missing
timestamps and observed close spreads. Model lab shows stored candle counts and
date ranges independently of its 300-candle chart. Dates alone are never approval.

The operator confirmed OANDA Canada. Coverage now includes documented New York
DST, daily breaks and verified Christmas 2025/New Year 2026 overrides. Older
approximate reports remain preserved; unresolved historical holiday gaps are not
guessed. See [the complete sixteen-series audit](HISTORICAL_DATA.md). This is not
execution-quality attestation.

All sixteen downloaded series pass research coverage requirements: one year for
most series, two years for FX hourly and six months for crypto 1m/15m. Model
qualification is separate. Scheduled training currently uses five-minute data only.

## Actual real-data model results

Two fixed logistic trend baselines used the full-year five-minute Forex data.
Spreads were measured from the first historical week, before held-out periods:
EUR/USD median 0.00016; GBP/USD median 0.00019. Slippage was one configured tick;
fee and financing assumptions were the current PAPER settings, zero. These are
explicit simulation assumptions, not independently verified broker charges.
Separate immutable plans were written before fitting. Initial p99-spread attempts
failed before creating artifacts; no held-out results were used to select costs.

| Model | Calibration samples | Validation Brier / baseline | Test Brier / baseline | Trades at 80% | Status |
| --- | ---: | --- | --- | ---: | --- |
| candidate-logistic-911b20642e3e2a11 (EUR_USD) | 339 | 0.59424 / 0.58801 | 0.55931 / 0.53416 | 0 | REJECTED |
| candidate-logistic-2a9e025c816228b2 (GBP_USD) | 494 | 0.55877 / 0.55517 | 0.59467 / 0.57333 | 0 | REJECTED |

Both failed activity/economic/uncertainty and Brier-baseline gates. Full base and
doubled-cost portfolio assessments are persisted in the database reviews and
research volume. No execution threshold changed. Final test results must not be
used for subsequent tuning or algorithm selection. Future comparisons need an
explicit validation-only selection plan and a genuinely untouched final period.
New validation-only comparisons include logistic, Random Forest, LightGBM and
XGBoost with three pre-test purged expanding folds and policy v3. Final scores are
sealed, including direct replay. Weekly jobs run separately from trading; see
[controlled learning](CONTROLLED_LEARNING.md). Real costs, feature/strategy tuning,
prospective final evaluation and regime robustness remain research requirements.

## Formal paper trials

Proposed `paper-trial-policy-v1` requires 30 wall days, 20 days of valid
model-observed duration, 100 closed trades, 20 active exit days, positive net P&L,
profit factor at least 1.2, sampled drawdown at most 8%, and target calibration
error at most 0.05 on at least 100 attributed closed outcomes. These are proposed
criteria, not approved operator requirements or proof of profitability.

Commands propose and explicitly approve an immutable policy, bind exactly current
verified models/runtime costs, and start from a flat reconciled account. Prior
infrastructure recordings cannot count as model trials. Deployment changes and
invalid evidence suspend new entries atomically while position monitoring continues.
Reports scope orders to their deployment and run, distinguish realized paper P&L
from infrastructure observations, and expose selection-biased fill calibration
explicitly. Closed UTC daily/weekly files are exported hourly by the worker.
No report automatically approves a model or broker execution.

No policy was approved and no model performance trial started: neither model
qualifies. The existing run remains infrastructure observations only.

```powershell
docker compose exec backend python -m app.cli trial-policy --models VERSION --output data/reports/trial-proposal.json
docker compose exec backend python -m app.cli trial-approve data/reports/trial-proposal.json --operator local-operator --reason "Approve predeclared supervised PAPER trial"
# Stop the infrastructure recorder first; POLICY_ID is printed by explicit approval.
docker compose exec backend python -m app.cli paper-record-start --symbols EUR_USD --trial-policy POLICY_ID
docker compose exec backend python -m app.cli trial-report RUN_ID --output data/reports/trial-evaluation.json
```

VERSION/POLICY_ID/RUN_ID are placeholders. Approval rejects unsupported or weakened
criteria and requires eligible active models. This local operator label is an
audit attribution, not authenticated multi-user identity.

## OANDA practice evidence

Added read-only account properties/details, pricing/home conversions and trade
lookup. Validation verifies accessible non-MT4 account, Decimal instrument
precision/units/margin, fresh tradeable quotes and a stable transaction watermark.
Home conversion uses separate broker factors for gains, losses and position value;
the shared risk engine supports these without assuming USD-to-CAD parity.
Native protection validation requires matching pending stop and target orders on
the confirmed trade and exact reserved exposure. It is unit-tested, not externally
verified on a submitted trade.

Actual API checks passed against the configured CAD practice account. There were
zero open trades, zero pending orders and zero nonzero positions. The initial
check incorrectly interpreted 14 zero-unit position records as exposure; fixed
and rechecked. No account ID or credentials are in this document.

```powershell
docker compose exec backend python -m app.cli practice-check --output data/reports/practice-readiness.json
```

Read-only readiness does not enable submission. Durable account-locked reservations,
cursor replay, uncertain-send quarantine, protected-fill verification, conservative
partial-reduction handling, net-cost closure accounting and practice worker recovery
are implemented and fault-tested with mocks. Actual read-only cursor reconciliation
reached 810 without discrepancies and retained suspension. The separately authorized
external lifecycle test, notification delivery and sustained recovery remain
unverified. See [broker acceptance](BROKER_INTEGRATION.md). No practice order,
notification or live-money action was performed.

## Verification and continuation

199 backend tests passed including PostgreSQL cases; 15 frontend tests passed;
frontend production build, Ruff, schema 0007 consistency and stack smoke checks
passed, including the common-period comparison and cashflow/summary regressions.
Trial/gateway positive authority is explicitly mocked in
tests. Real elapsed model-performance evidence is absent. Outcome attribution,
two-window drift diagnostics, explicit suspension policy and a separate weekly
research worker are implemented. Scheduled candidates cannot promote; prospective
untouched final evaluation now has a one-shot reservation/finalization workflow
(schema 0008), but no current candidate passes its validation prerequisite. Further model research and
independent feature/strategy/cost/regime validation remain necessary.

Local `.env` had been changed to live enabled and ten positions; restored to live
disabled and the mandated three-position cap, preserving credentials and PAPER mode.
