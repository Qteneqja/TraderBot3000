# Simulation methodology

The simulator supports conservative single-trade outcomes and chronological single-instrument portfolio replay. Multi-asset portfolio research remains incomplete.

Market entries use next-bar open plus executable half-spread and adverse slippage. Gaps beyond protective levels invalidate entry. Limit orders require strict executable-side penetration; touching the level is insufficient. Pending orders expire after a bar budget. No optimistic gap improvement is assumed.

Long exits use modeled bid, shorts modeled ask. If stop and target touch in one candle, stop wins. Stop gaps fill at the worse opening price plus slippage. A same-bar target after limit entry is not credited when ordering is unknown. Timeouts use executable close. Fees apply on both legs, with optional per-bar financing.

Costs are explicit constants; preserved OANDA bid/ask OHLC, partial fills, depth and latency are not yet consumed. The older `backtest-demo` uses fixed 100-unit positions to exercise mechanics. `backtest-model` uses the shared risk engine, strategy proposals and exit resolver. It reserves risk and full notional margin, allows overlapping positions within caps, marks equity, tracks daily/weekly loss and drawdown, stops after consecutive losses, and applies fees and financing. Quantities and accounting use Decimal. Assumed-spread candles are not execution-quality evidence.

The registered-model command accepts only held-out validation or test ranges and verifies the artifact and original input candle manifest before simulation. It preserves an immutable JSON report containing risk settings, provenance, costs, trades, rejection counts and equity. Experimental model eligibility within this isolated research simulation does not authorize deployment or change registry status. No broker or paper-gateway submission occurs.

Metrics: net return, mark-to-market drawdown, win rate, profit factor, expectancy, equity/drawdown paths, exposure fraction, average holding bars, fees and a zero-return no-trade benchmark. Profit factor is null without losses. Annualization/Sharpe remain null without a validated schedule. Cross-asset correlation, sensitivity sweeps, richer baselines, Sortino and confidence intervals are outstanding.

Tests cover side-aware costs, ambiguity, unfilled limit touches, adverse stop gaps, invalidated entry gaps, shared risk limits, overlapping position accounting and insufficient-model abstention. The verified synthetic candidate run returned zero trades at the unchanged 80% threshold. Synthetic output must never be presented as evidence for deployment.

Model assessment replays both held-out partitions with base costs and a twofold multiplier across spread, slippage, fees and financing. It records a circular-block daily P&L uncertainty diagnostic and fails a stress run that merely abstains. This single stress scenario is not a complete sensitivity sweep or regime study. See [MODEL_ACCEPTANCE.md](MODEL_ACCEPTANCE.md).
