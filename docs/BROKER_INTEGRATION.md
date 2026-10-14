# OANDA practice integration

Implemented transport: practice-only authentication, account summary, instruments, pending orders/open trades, transaction lookup and client-ID lookup. The market-order schema builder includes FOK, OPEN_ONLY, priceBound, client IDs and stop/target-on-fill. Trade-specific closure requires positive units and does not retry uncertain outcomes.

**Submission is disabled.** Durable broker reservations, startup transaction reconciliation, account currency/margin validation, limit/stop entries, unprotected-fill recovery and autonomous practice management remain incomplete. Direct `submit()` calls fail closed, and the practice worker refuses to start.

Next integration sequence:

1. Validate the actual non-MT4 practice account, instruments, units, price precision and conversion/margin rules.
2. Reconcile orders/trades and transactions with a durable cursor; quarantine unexpected positions and unknown states.
3. Lock account risk, persist an immutable approved reservation and unique client ID before POST.
4. Parse create/fill/reject/cancel transactions; HTTP success alone is not fill confirmation.
5. On timeout, persist UNKNOWN and reconcile. Never blindly repeat POST; a single 404 is insufficient proof of no execution.
6. Verify protection on every confirmed trade before clearing account suspension.
7. Test network/process failures, then verify against operator-supplied practice credentials.

Coinbase execution and live trading are unsupported. Crypto stays analysis/paper-only; Canadian account eligibility, shorting, leverage and supported orders must be verified separately.

Sources: [OANDA order definitions](https://developer.oanda.com/rest-live-v20/order-df/), [order endpoints](https://developer.oanda.com/rest-live-v20/order-ep/), [trade endpoints](https://developer.oanda.com/rest-live-v20/trade-ep/). Do not use client extensions on MT4-linked accounts.
