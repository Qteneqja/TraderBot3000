# Live readiness: NOT READY

Real-money execution is unsupported. LIVE mode and ENABLE_LIVE_TRADING=true are rejected during configuration. No live credentials, URL or activation endpoint exist. Software tests do not establish trading readiness.

Required before a separately authorized live implementation:

- Complete practice gateway, durable reconciliation, unknown-order recovery, currency/margin rules and protection enforcement.
- Validate licensed real history and execution-quality bid/ask costs; align training outcomes with actual entries.
- Predeclare numerical acceptance criteria using research/validation data: net expectancy, confidence intervals, drawdown, calibration, trade counts, costs and regime stability. Do not tune on final tests.
- Extend the tested PAPER deployment/rollback workflow to independently reviewed broker promotion; implement drift controls, verified sessions, quality circuit breakers and optional economic-event restrictions.
- Verify jurisdiction and actual broker/exchange account eligibility, including crypto order capabilities.
- Run sustained paper/practice soak tests and network, restart, database, missing-protection and incident-recovery drills.
- Add operator identity, auditable staged activation, separate live credentials, explicit caps, monitoring and tested restore procedures.
- Obtain a distinct operator decision after reviewing strategy and operational evidence.

There is no demonstrated trading advantage or reliable autonomous broker operation yet. Remain in research/paper mode. Choosing no trade is an intended outcome.
