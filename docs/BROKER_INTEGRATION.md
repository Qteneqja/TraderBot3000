# OANDA practice integration

Implemented transport: practice-only authentication, account summary, instruments, pending orders/open trades, transaction lookup and client-ID lookup. The market-order schema builder includes FOK, OPEN_ONLY, priceBound, client IDs and stop/target-on-fill. Trade-specific closure requires positive units and does not retry uncertain outcomes.

**Submission remains disabled locally.** Migration 0006 implements account-locked reservations, transaction-cursor replay, native-protection verification and a gated practice worker. Direct adapter submission still fails closed; only a committed gateway reservation can send. Market FOK / OPEN_ONLY entries are supported for EUR_USD and GBP_USD. Pending limit/stop entries remain unsupported.

Required acceptance sequence before practice submission:

1. A real-provider model passes every current research gate, independent execution-quality review and explicit PAPER activation. No current model qualifies.
2. Its explicitly approved paper trial completes duration, sample, risk, calibration and reliability requirements. Infrastructure recording alone is insufficient.
3. Current read-only account/instrument checks and durable reconciliation pass, without foreign exposure, unknown reservations or unreviewed cost overruns.
4. Obtain explicit operator authorization for one small practice test. Default authorization permits at most one order of one unit. The signal must independently qualify; no demonstration bypass exists.
5. Observe real create/fill/native protection, closure, net costs and notification delivery. Restart with owned exposure and verify cursor/protection/risk recovery without duplicate execution. Record the external lifecycle review. Mocks cannot satisfy these external requirements.
6. Obtain a separate explicit autonomous authorization bound to that successful test approval, current model/runtime and completed trial. Keep live money unsupported.

The gateway commits SUBMITTING before POST and CLOSING before one trade-specific PUT. A timeout, crash, HTTP success or isolated client-ID 404 cannot justify another submission. UNKNOWN retains reserved risk and suspension until positive evidence/operator review resolves it. Reconciliation requires ordered contiguous transactions and a stable snapshot watermark. It checks ownership, signed position totals, native protection and request hashes. Unexpected exposure, partial reductions and mismatches suspend entries. Partial reductions retain conservative reserved risk; final outcomes use cumulative broker trade P&L, financing/dividend adjustments and allocated commissions. Approved emergency management can close owned unprotected exposure without reversing aggregate positions or adopting foreign trades.

Decimal risk uses distinct broker gain, loss and position conversion factors, instrument precision and margin requirements. SQLite/PostgreSQL mocks cover concurrent duplicate reservations, crashes before/after send, timeout-before/after-fill, transaction gaps, foreign exposure, protection failures, expiry/close idempotency, fees/financing and restart reconciliation. Positive model/trial authority is explicitly mocked.

Read-only verification on October 14, 2026 UTC: configured OANDA Canada practice account is non-MT4, CAD, with positive NAV/free margin, valid EUR/GBP precision/conversions and zero trades/pending orders/nonzero positions. Durable reconciliation reached cursor 810 with no discrepancies and retained `suspended=true`, `submission_enabled=false`. No account ID or credential is exposed through dashboard/report summaries. This does not verify real fill/protection/close behavior.

```powershell
docker compose exec backend python -m app.cli practice-check --output data/reports/practice-readiness-UNIQUE.json
docker compose exec backend python -m app.cli practice-reconcile
```

The local authorization commands are `practice-authorize --trial RUN --operator NAME --reason TEXT`, `practice-lifecycle-approve ORDER --operator NAME --reason TEXT` and the separate `practice-authorize --autonomous ...`. They are not routine startup commands. Invoke them only after the acceptance evidence exists and the user explicitly approves the corresponding external action. Actual submission, slippage, protection execution, notifications and sustained recovery remain externally unverified.

Coinbase execution and live trading are unsupported. Crypto stays analysis/paper-only; Canadian account eligibility, shorting, leverage and supported orders must be verified separately.

Verification on October 14, 2026 (UTC): after the operator updated ignored `.env`, read-only OANDA practice EUR/USD candles and account-summary requests both returned HTTP 200. Credentials and account access are verified for those endpoints. This does not verify order execution, protection, transactions or reconciliation. No practice orders were submitted and no live endpoint was tried.

Sources: [OANDA order definitions](https://developer.oanda.com/rest-live-v20/order-df/), [order endpoints](https://developer.oanda.com/rest-live-v20/order-ep/), [trade endpoints](https://developer.oanda.com/rest-live-v20/trade-ep/). Do not use client extensions on MT4-linked accounts.
