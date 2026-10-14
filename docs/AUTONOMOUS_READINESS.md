# Remaining autonomous milestones: October 14, 2026 UTC

## Verified research milestone

The CLI now accepts explicit inclusive `--start` and exclusive `--end` for
`train-candidates`. The new `data-report` command generates immutable reports with
manifest, usable days/windows, duplicate/future checks, session estimates, missing
timestamps and observed close spreads. Model lab shows stored candle counts and
date ranges independently of its 300-candle chart. Dates alone are never approval.

The weekly OANDA estimate uses New York time and DST, based on
[OANDA's published hours](https://www.oanda.com/us-en/trading/hours-of-operation/).
It is approximate: [Canadian daily breaks](https://www.oanda.com/ca-en/trading/hours-of-operation/)
and historical holiday overrides still need account-specific validation. Unknown
holidays are reported as unexplained gaps. This is not execution-quality attestation.

In addition to the full-year five-minute history, six-month provider downloads
for one-minute, fifteen-minute and hourly data completed for all four instruments,
2026-04-14 through 2026-10-14. Their detailed coverage assessments remain pending.

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
Crypto models, gradient-boosted comparisons, walk-forward selection, independently
validated fees/costs and regime robustness remain unfinished.

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

Read-only readiness does not enable submission. Durable reservations, transaction
reconciliation, uncertain submission/closure recovery, complete worker integration,
and explicitly authorized practice lifecycle testing remain unfinished. Direct
submission remains disabled. No practice order, notification or live-money action
was performed.

## Verification and continuation

141 backend tests passed including PostgreSQL cases; 11 frontend tests passed;
frontend production build and Ruff passed. Database migration/smoke verification
must also pass for deployment. Trial orchestration uses explicitly mocked passing
research evidence in tests, not actual eligible models. Real elapsed performance
evidence is absent. Model promotions remain explicit. Learning outcome attribution,
drift reports, scheduled retraining and comparison infrastructure remain pending.

Local `.env` had been changed to live enabled and ten positions; restored to live
disabled and the mandated three-position cap, preserving credentials and PAPER mode.
