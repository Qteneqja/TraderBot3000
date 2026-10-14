# Risk management

The pure `approve()` function has final authority over paper entry. Submission locks the account and requires an ACTIVE execution-validated model scoped to source/instrument/strategy/timeframe. Candidate-supplied calibration alone is insufficient. No deployed model ships with the app.

Limits: 0.5% planned trade risk, 2% daily loss, 5% weekly loss, 1.5% total planned risk, 1% conservative global correlated risk, three positions, 3x leverage, 10% peak drawdown and five consecutive losing closures. Limits can be tightened. Gaps/outages can cause larger realized losses than planned.

```
fees_allowance = (entry + max(stop, target)) * fee_rate + financing_allowance
loss_per_unit = (stop_distance + entry_deviation + spread + 2*slippage + fees_allowance) * quote_to_account
risk_budget = min(trade_budget, remaining_portfolio_budget, remaining_correlation_budget)
size = min(risk_budget / loss_per_unit, units_affordable_with_margin_and_entry_fee, units_under_leverage_cap)
units = floor(size / unit_step) * unit_step
planned_risk = units * loss_per_unit
```

Decimal quantities round down. Minimum sizes, tick precision, notional leverage, margin, total and correlated risk are enforced. Available margin caps size rather than rejecting every full-risk proposal that is too large. Paper reserves full notional margin. Slippage cannot move the entry beyond protection. General account currency conversion and broker rules are not connected; broker execution remains blocked.

Other gates: correct stop/target direction, minimum 2:1 reward/risk, matching source, signal expiry, fresh quotes/account state, spread, entry drift and eligible regime. EV uses calibrated target/stop/timeout probabilities, conservatively treating timeouts as full stop losses and charging costs.

Persisted account state includes UTC day/week equity anchors, peak equity, consecutive losses, reconciliation and suspension. Equity includes open-position quote marks. Stale marks or mismatched sources block entry. Restart reconciliation blocks unknown paper orders, invalid protection or missing execution-cost contracts. Worker-dependent paper stops are not broker-held protections.

Paper orders retain their quote source, fee rate, slippage and financing assumptions. Entry and exit fees are deducted once; financing accrues once per started holding bar and persists across restarts. Net P&L includes every recorded charge. Existing positions keep their original assumptions when configuration changes. The default zero fee/financing and one-tick slippage are software-demo settings, not actual broker pricing; configure `PAPER_FEE_RATE`, `PAPER_SLIPPAGE_TICKS` and `PAPER_FINANCING_PER_UNIT_PER_BAR` before any execution validation. Legacy open positions without this contract are suspended for investigation.

`POST /api/admin/suspend` requires `Authorization: Bearer ADMIN_TOKEN`, audits the action and blocks new entries while monitoring continues. No web resume exists yet. Incident response: suspend, stop worker if needed, inspect persisted state, resolve uncertainty and restart through reconciliation. Do not erase orders to hide unknown outcomes.
