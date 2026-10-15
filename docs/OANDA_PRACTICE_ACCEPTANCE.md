# OANDA practice acceptance

As of 2026-10-15 UTC: **READ-ONLY CONNECTIVITY VERIFIED; SUBMISSION DISABLED**. Division Canada, account currency CAD. Actual practice orders **0**; stored practice open/closed orders **0/0**. The read-only flat-account check passed. Real-money execution remains unsupported.

The latest cost observation passed accessible non-MT4 account, positive NAV/free margin, instrument contracts, supported protection mode, fresh/tradeable quotes, distinct home-currency conversions, flat-account, transaction endpoint and stable watermark checks. No balances, account identifiers or raw broker payloads are published here. Prior reconciled cursor 810 remains preserved with suspension retained.

Current account access is not order acceptance. Native protection, reconciliation, uncertain-send quarantine, cursor replay, partial-reduction handling and fee-aware closures are implemented and fault-tested with mocks. Actual submitted/recovered/protected orders remain **externally unverified**. No new authorization to submit an order was inferred from this report.

Complete every acceptance item in [BROKER_INTEGRATION.md](BROKER_INTEGRATION.md) before enabling practice submission, including eligible frozen models, accepted formal PAPER evidence, verified costs/contracts, explicit operator approval, confirmed protective stop/target, reconciliation after disconnect/restart and verified trade notifications. A missing protection or unknown-send state must retain suspension and must not blindly retry an order.

```powershell
docker compose exec backend python -m app.cli practice-check --output data/reports/practice-readiness-NEW-UNIQUE.json
```

This command is read-only. Broker submissions remain gated. Account-specific commission and historical financing are still UNKNOWN; see [execution-cost validation](EXECUTION_COST_VALIDATION.md).
