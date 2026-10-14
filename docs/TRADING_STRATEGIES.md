# Strategy hypotheses

Every strategy is RESEARCH with no established advantage. None generates a probability.

| Strategy | Hypothesis | Regime |
|---|---|---|
| Trend | EMA spread exceeds a minimum | Bullish/bearish trend |
| Momentum | RSI and rate of change agree | Trend |
| Mean reversion | Rolling z-score exceeds ±2 | Range |
| Breakout | Close exceeds previous 20-bar range | Trend or range |
| Structure | Close breaks a confirmed swing | Trend |
| Volatility | Return exceeds 1.5 rolling deviations | Trend |

Features include returns, volatility, ATR, RSI, MACD, EMA spread, z-score, ROC and ADX. ATR/ADX use recursive smoothing; parity against an independent indicator library remains to be tested. Related indicators are not independent probability evidence.

Regimes are bullish/bearish trend, range, high/low volatility and uncertain. Thresholds are provisional. Uncertain/excessive-volatility conditions abstain. Pivots become known two bars after their source; breakout ranges are shifted. Higher-timeframe alignment joins candle completion times. Tests confirm future bars do not alter prior features/signals.

Entry proposes the completed close, stop is 1.5 ATR, target is 2.5 stop distances, with tick quantization and one-interval expiration. These policies have no claimed performance advantage. Higher-timeframe confluence is a tested join utility, not yet a separate integrated registry strategy.
