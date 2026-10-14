# Research acceptance and remaining deployment gates

The `research-screen-v1` policy is a conservative engineering screen, not an empirically established promise of profitability or a completed execution-approval system. It is included in each new candidate artifact and dataset version before fitting. Its hash includes the risk settings; altering thresholds after viewing final outcomes invalidates reuse of the original assessment policy. Older artifacts lacking a declared policy must be retrained as a new experiment. Never retrofit a policy into an old manifest or repeatedly optimize against the test partition.

`python -m app.cli acceptance-policy` displays the exact policy. `python -m app.cli assess-model VERSION` verifies the registered artifact and checks prerequisites before inspecting held-out portfolios. Reviews are stored under content-derived IDs in `model_reviews`, audited once, and exposed read-only in Model lab. Registry status and execution eligibility remain unchanged.

Preconditions: recognized provider source, at least 180 calendar days of input history, 200 calibration candidates, verified artifact metadata, unchanged policy/risk settings, PAPER research mode, at least 80% target threshold and 2:1 reward/risk. Fixture data cannot qualify. These duration/count checks do not establish complete market coverage, licensing or execution-quality data; those require independent review.

Each held-out validation and test partition must independently satisfy:

- At least 30 calendar days, 100 closed trades and 20 active exit days.
- Positive net return and expectancy, profit factor at least 1.2 and drawdown no greater than 8%.
- Target calibration error at most 0.05 and multiclass Brier score better than the training-class-frequency baseline.
- A positive lower percentile bound for mean daily realized net P&L under the declared circular block bootstrap.
- At least 100 trades, positive return and drawdown at most 8% when spread, slippage, fees and financing are doubled. Abstention under stress does not count as robust profitability.

The bootstrap includes zero-activity calendar days and resamples circular five-day blocks with 2,000 draws and seed 42. It reports 2.5th/97.5th percentile bounds. Blocks retain nearby dependence but do not establish stationarity, eliminate selection bias or guarantee interval coverage. Fixed block length, realized rather than intraday returns, limited regime coverage and multiple experiments remain limitations. The approach follows the [circular-block method described in the arch documentation](https://bashtage.github.io/arch/bootstrap/timeseries-bootstraps.html); the small implementation uses NumPy and does not add an arch dependency.

Held-out replay checks the original candle manifest. Base and stressed replay hashes, summary metrics, policy, failures and uncertainty diagnostics persist in each review. Nonfinite evidence cannot receive an attestation. A missing or invalid prerequisite yields REJECTED without running the portfolio evaluations. Repeated identical assessment is idempotent.

`RESEARCH_GATES_PASSED` means further review is warranted. It is not ACTIVE, APPROVED or execution authorization. Independent regime/cost validation, a real-time paper soak, runtime inference approval, deployment leasing and audited activation/rollback are still required. No CLI or API activation path is added by this milestone. The current synthetic experiment is correctly rejected for source, short history and calibration count.
