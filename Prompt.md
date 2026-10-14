# MASTER DEVELOPMENT PROMPT

## Autonomous AI & Machine Learning Trading Intelligence Platform

### YOUR ROLE

You are acting as an elite multidisciplinary software engineering and quantitative research team consisting of:

* Principal AI and Machine Learning Engineer
* Senior Quantitative Trading Researcher
* Algorithmic Trading Systems Engineer
* Senior Python Backend Engineer
* Financial Data Engineer
* Statistical Learning and Time-Series Specialist
* Risk Management Systems Architect
* Trading Infrastructure Engineer
* Senior React/TypeScript Frontend Engineer
* DevOps and Cybersecurity Engineer
* Software Quality Assurance Engineer

You have extensive expertise in quantitative finance, algorithmic trading, machine learning, statistical modelling, financial market microstructure, trading system architecture, and autonomous software systems.

Your responsibility is to **design, implement, integrate, test, and document a complete autonomous AI-powered trading intelligence platform**.

Do not merely explain how to build the application.

Actually create the required project structure, write the implementation, configure the infrastructure, implement tests, and produce a working application.

Use production-quality engineering practices while maintaining a manageable architecture appropriate for a single developer.

The final system must be designed to operate continuously, analyze live financial markets, identify trading opportunities, determine entry and exit levels, enforce risk restrictions, execute qualifying trades automatically through supported broker APIs, monitor positions, and evaluate its own performance.

### CRITICAL DEVELOPMENT PRINCIPLES

1. Never assume a trading strategy is profitable without evidence.
2. Never fabricate historical data, market prices, trading performance, or model confidence.
3. Never use future market information to make historical predictions.
4. Never represent an arbitrary strategy score as a calibrated probability.
5. Never allow an LLM to bypass risk management or independently authorize execution.
6. Never enable real-money trading by default.
7. Never expose API credentials.
8. Never introduce unintended duplicate orders.
9. Never assume an order has executed without confirmation.
10. Never optimize solely for historical win rate.
11. Never use simulated results as evidence of guaranteed future returns.
12. Every model and strategy must be evaluated using realistic, reproducible, out-of-sample testing.
13. The system must safely abstain from trading when conditions are unsuitable.
14. Live trading must require a separate, explicit operator activation process.
15. Prioritize correctness, safety, and reproducibility over adding unnecessary complexity.

---

# 1. PROJECT OBJECTIVE

Build a platform named:

**AegisTrade AI**

The application will monitor Forex and cryptocurrency markets using historical and real-time financial data.

Its purpose is to identify statistically promising trading opportunities using a combination of:

* Technical analysis
* Price action
* Market structure
* Quantitative trading strategies
* Statistical forecasting
* Machine learning
* Market regime detection
* Probability estimation and calibration
* Volatility analysis
* Risk-adjusted opportunity evaluation
* LLM-generated analysis and explanations

When a trading opportunity satisfies all configured requirements, the platform must calculate:

1. Trading instrument
2. Trade direction: LONG or SHORT
3. Recommended entry price or entry zone
4. Order type
5. Stop-loss price
6. Take-profit price
7. Optional additional take-profit targets
8. Estimated probability of achieving the defined trading outcome
9. Expected return after estimated trading costs
10. Reward-to-risk ratio
11. Position size
12. Maximum planned account risk
13. Signal expiration
14. Strategy responsible for the signal
15. Market conditions supporting the signal
16. Conditions that would invalidate the trade
17. Human-readable AI explanation

The platform must support complete autonomous execution once explicitly enabled.

It must also support independent monitoring and paper trading without requiring real money.

**Important:** This project targets ordinary long/short market positions, not short-expiry binary options. Actual options-contract trading is outside the initial scope.

---

# 2. INITIAL MARKETS

Implement support for the following markets.

### Forex

Broker and execution provider:

**OANDA v20 REST API**

Initial instruments:

* EUR/USD
* GBP/USD

Design the system so additional OANDA-supported instruments can be configured without modifying core trading logic.

### Cryptocurrency

Initial market data provider:

**Coinbase Advanced Trade public market data APIs**

Initial instruments:

* BTC/USD
* ETH/USD

Cryptocurrency trading must initially operate in analysis and paper-trading modes.

Create an extensible cryptocurrency execution interface, but do not assume Coinbase or any other exchange permits every order type, leveraged trade, or short position for Canadian accounts.

Do not activate cryptocurrency live execution until a supported exchange, jurisdictional eligibility, account permissions, and execution capabilities have been verified.

### Timeframes

Support:

* 1-minute data for execution analysis where available
* 5-minute trading timeframe
* 15-minute trading timeframe
* 1-hour trading timeframe
* Optional 4-hour context

The platform must support multi-timeframe analysis.

Higher-timeframe features must only use completed candles available at the prediction timestamp.

---

# 3. TECHNOLOGY STACK

Use the following technologies unless a better choice is justified.

### Backend

* Python 3.12+
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* Pandas
* NumPy
* PyArrow
* HTTPX
* WebSockets or provider-supported streaming clients

### Machine Learning

* Scikit-learn
* LightGBM
* XGBoost
* Optuna
* Joblib
* MLflow or an appropriately lightweight model registry

### Statistical Analysis

* SciPy
* Statsmodels
* Appropriate numerical and statistical libraries

### Technical Indicators

Use established technical analysis libraries where appropriate.

Implement custom indicators only when necessary.

Ensure every feature can be computed causally without future information.

### Backtesting

Evaluate established backtesting libraries such as VectorBT.

Implement custom execution simulation components where required for realistic broker-specific behaviour.

Prioritize correctness and reproducibility over library convenience.

### LLM

Default provider:

**DeepSeek API**

Default model:

`deepseek-flash`

Use the provider's currently supported API.

Create a provider abstraction that also supports optional OpenAI integration.

### Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* TradingView Lightweight Charts or an equivalent open-source charting library

### Infrastructure

* Docker
* Docker Compose
* GitHub
* Environment-based configuration
* Structured application logging

The system must run locally before cloud deployment.

Design cloud deployment so it can later operate continuously on AWS.

Do not introduce Kubernetes, Kafka, or unnecessary distributed infrastructure during the initial implementation.

---

# 4. HISTORICAL MARKET DATA ENGINE

Develop a reliable historical data ingestion system.

The platform must automatically collect and store available historical market information.

Target several years of market history where provider availability and licensing permit.

### Required functionality

1. Download historical candles.
2. Support configurable trading instruments.
3. Support multiple timeframes.
4. Retrieve available bid/ask information.
5. Respect provider pagination and rate limits.
6. Resume interrupted downloads.
7. Avoid duplicate records.
8. Detect missing periods.
9. Identify invalid prices.
10. Identify anomalous timestamps.
11. Detect incomplete candles.
12. Normalize timestamps into UTC.
13. Preserve source metadata.
14. Track data provenance.
15. Validate chronological ordering.
16. Maintain ingestion logs.
17. Incrementally update datasets.

Store historical information using PostgreSQL and compressed Parquet files where appropriate.

Do not invent candles to fill missing data.

Market closures, weekends, holidays, and genuine data gaps must be handled differently.

Historical data must not be considered execution-quality unless the relevant bid/ask, spread, and fill assumptions have been validated.

### Required data structures

Implement models for:

* Instruments
* Market candles
* Market ticks or quotes
* Bid/ask spreads
* Data ingestion jobs
* Data quality reports
* Provider metadata
* Market trading sessions

The ingestion system must support both historical backfilling and incremental updates.

---

# 5. LIVE MARKET DATA ENGINE

Create a real-time market monitoring service.

### Forex

Use OANDA pricing streams where supported.

### Cryptocurrency

Use Coinbase WebSocket market data.

### Requirements

Implement:

* Persistent market-data connections
* Heartbeat monitoring
* Automatic reconnection
* Exponential backoff
* Rate-limit handling
* Stream interruption detection
* Stale quote detection
* Timestamp validation
* Duplicate event handling
* Instrument status monitoring
* Candle construction
* Safe shutdown
* Automatic recovery

The market-data service must distinguish between:

* Live quotes
* Completed candles
* Incomplete candles
* Stale market data
* Unavailable instruments

Trading decisions must only use information available at the time of evaluation.

A stale or unreliable data feed must prevent new order execution.

The system should continue safely managing existing positions through broker-held protective orders whenever supported.

---

# 6. QUANTITATIVE TRADING STRATEGY ENGINE

Implement a modular strategy framework.

Strategies must be independent, configurable, testable, and replaceable.

Do not assume a strategy is effective because it is popular or widely discussed.

Treat every strategy as a hypothesis requiring empirical validation.

### Strategy A: Trend Following

Evaluate:

* Exponential moving averages
* Trend direction
* ADX
* Higher-timeframe confirmation
* Trend persistence
* Pullbacks
* Volatility-adjusted entries

### Strategy B: Momentum

Evaluate:

* RSI
* MACD
* Rate of change
* Momentum acceleration
* Relative strength
* Price continuation
* Available volume indicators

### Strategy C: Mean Reversion

Evaluate:

* Bollinger Bands
* Z-scores
* Distance from moving averages
* Price deviations
* Historical reversion behaviour
* Volatility conditions

### Strategy D: Breakout Trading

Evaluate:

* Consolidation ranges
* Donchian Channels
* Support and resistance
* Previous highs and lows
* Breakout strength
* Retests
* False breakout behaviour

### Strategy E: Market Structure

Identify causally defined:

* Swing highs
* Swing lows
* Higher highs
* Higher lows
* Lower highs
* Lower lows
* Structure breaks
* Support and resistance zones
* Liquidity-sensitive price areas

Do not use repainting indicators or swing-point definitions that require future candles without explicitly delaying recognition until confirmation.

### Strategy F: Volatility-Based Trading

Evaluate:

* ATR
* Historical volatility
* Volatility expansion
* Volatility contraction
* Volatility-adjusted stop distances
* Volatility regime changes

### Strategy G: Multi-Timeframe Confluence

Evaluate whether shorter-timeframe opportunities align with broader market conditions.

Higher-timeframe confirmation must be based on information available when the trade would have been entered.

### Strategy Selection

Create a strategy registry.

Each strategy must output a standardized candidate object containing:

* Strategy identifier
* Instrument
* Direction
* Timestamp
* Proposed setup
* Supporting features
* Invalidation conditions
* Strategy-specific metrics

Do not blindly combine every indicator.

Closely correlated indicators must not be treated as independent evidence.

The system must be able to disable strategies that fail validation or become statistically unreliable.

---

# 7. MARKET REGIME DETECTION

Develop a market regime classification component.

Initially support:

1. Strong bullish trend
2. Strong bearish trend
3. Range-bound market
4. High-volatility conditions
5. Low-volatility conditions
6. Uncertain or transitional conditions

Start with interpretable statistical and rule-based methods.

Evaluate whether machine learning improves regime classification.

Potential models include:

* Gradient boosting
* Hidden Markov Models
* Clustering algorithms
* Statistical volatility models

Select methods based on demonstrated performance.

The regime detector must not use future market movements to label the current live regime.

Use market regime information to determine which strategies are eligible for evaluation.

The system must support an uncertain classification that reduces activity or blocks new trades.

---

# 8. MACHINE LEARNING PREDICTION ENGINE

Develop the platform's primary predictive intelligence.

Use LightGBM and XGBoost as initial candidate models.

Compare them against:

* Logistic regression
* Simple directional baselines
* Rule-based trading strategies
* Other appropriate benchmark models

Do not automatically choose the most complicated model.

### Prediction objectives

The system should evaluate:

1. Probability of a favourable directional movement.
2. Probability of reaching a proposed take-profit before a proposed stop-loss.
3. Probability of a stop-loss being reached first.
4. Probability that neither barrier will be reached before the allowed holding period expires.
5. Expected trading return after costs.
6. Market conditions associated with prediction reliability.

Implement barrier-based labeling, including a properly designed triple-barrier methodology where appropriate.

For each candidate setup, define the proposed entry, stop-loss, take-profit, and maximum holding period using only information available before the outcome window.

For unfilled limit orders, model whether the proposed entry was reached before expiration.

Never label an unfilled order as a successful trade.

Avoid selection bias when optimizing candidate entries, stops, and take-profits.

### Features

Consider:

* Returns
* Rolling volatility
* ATR
* RSI
* MACD
* Moving averages
* Trend strength
* Support and resistance
* Market structure
* Time of day
* Trading session
* Spread
* Momentum
* Historical breakout behaviour
* Higher-timeframe features
* Available cryptocurrency volume information

Do not assume decentralized Forex tick volume is equivalent to actual centralized traded volume.

### Training and validation

Implement:

* Chronological training splits
* Walk-forward validation
* Purged or embargoed validation when label windows overlap
* Hyperparameter optimization
* Strict separation of training, validation, and final test datasets
* Model calibration
* Feature importance analysis
* Model artifact versioning
* Reproducible training runs

All preprocessing must be fitted on training data only.

The final untouched test dataset must not be repeatedly used to select features, tune parameters, or choose trading thresholds.

Report performance separately for Forex and cryptocurrency.

### Confidence calibration

The system must never produce arbitrary confidence scores.

Use appropriate calibration methods and evaluate:

* Reliability curves
* Brier score
* Log loss
* Calibration error
* Confidence bucket performance
* Out-of-sample signal frequency

An estimated 80% probability must correspond to a clearly defined event.

For example:

"The estimated probability that the specified take-profit is reached before the stop-loss within the next 60 minutes, conditional on entry being filled."

If confidence cannot be reliably calibrated, the system must explicitly report that limitation.

The system must support declining to trade when model uncertainty is excessive.

---

# 9. TRADE ENTRY OPTIMIZATION

Develop an entry selection module.

The module must determine whether immediate execution or a pending entry is preferable.

Evaluate:

* Market entries
* Limit entries
* Breakout entries
* Pullback entries
* Support/resistance retests
* Spread-sensitive execution
* Liquidity constraints
* Entry expiration
* Price movement since signal generation

For each candidate trade, calculate:

* Proposed entry price
* Permitted entry zone
* Entry type
* Maximum acceptable slippage
* Maximum acceptable spread
* Signal validity period

The system must not chase a price after the setup becomes invalid.

Pending signals must expire automatically.

Entry optimization must be evaluated on unseen historical data using realistic fill assumptions.

---

# 10. STOP-LOSS ENGINE

Develop a deterministic stop-loss calculation component.

Potential methods include:

* ATR-based stops
* Structural invalidation stops
* Recent swing-based stops
* Volatility-adjusted stops
* Strategy-specific stops

The chosen stop must reflect the actual reason the trading setup would be invalidated.

Validate:

* Correct stop direction
* Minimum broker stop distance
* Instrument precision
* Expected execution costs
* Spread
* Position risk
* Broker order requirements

Never widen a stop-loss merely to avoid recognizing a loss.

All stop modifications must follow a predefined and testable trade-management policy.

---

# 11. TAKE-PROFIT OPTIMIZATION

Create a take-profit engine supporting:

* Primary take-profit
* Optional TP1
* Optional TP2
* Optional TP3
* Time-based exits
* Strategy-specific exits

Evaluate targets using:

* Market structure
* Support/resistance
* Historical price movement distributions
* Volatility
* Estimated target-hit probabilities
* Expected returns
* Trading costs

Evaluate whether partial profit-taking or a single exit produces better results.

Multiple take-profit targets must be implemented in a manner compatible with the broker's actual execution capabilities.

Do not assume that multiple broker-native take-profit orders can be attached to one position.

If partial exits require application-managed orders, implement them safely, prevent over-closing or reversing positions, and keep the remaining exposure protected.

Initially prioritize one broker-held stop-loss and one executable primary take-profit over complex multi-target management.

---

# 12. EXPECTED VALUE AND TRADE APPROVAL ENGINE

Implement a final opportunity evaluation system.

Do not approve a trade simply because its predicted directional accuracy exceeds a threshold.

Evaluate:

* Calibrated outcome probabilities
* Potential reward
* Potential loss
* Trading costs
* Spread
* Slippage
* Financing or overnight costs where applicable
* Unfilled-entry probability
* Market uncertainty
* Available account margin
* Existing correlated exposure

Select opportunities based on conservative expected return and validated risk-adjusted performance.

A simplified expected value calculation may be used for initial evaluation, but the final implementation must also handle timeout exits and other outcomes.

Do not assume every trade ends precisely at its stop-loss or take-profit.

### Minimum requirements

Start with configurable research thresholds:

* Model probability threshold: 80%
* Minimum reward-to-risk ratio: 2:1
* Maximum spread relative to expected reward
* Maximum account risk per trade: 0.5%

These are initial research settings, not proven optimal parameters.

Use validation data to evaluate alternative thresholds.

Only deploy thresholds supported by out-of-sample evidence.

If no threshold produces acceptable performance, reject the strategy instead of forcing trading activity.

---

# 13. RISK MANAGEMENT ENGINE

Create an independent, deterministic risk engine.

The risk engine must have absolute authority over whether new orders are permitted.

Neither machine learning models nor LLM outputs may bypass it.

### Initial configurable risk limits

* Maximum planned risk per trade: 0.5% of account equity
* Maximum daily loss: 2%
* Maximum weekly loss: 5%
* Maximum simultaneous positions: 3
* Maximum aggregate portfolio exposure: configurable
* Maximum correlated exposure: configurable
* Maximum leverage: broker/account-aware
* Maximum spread: instrument-dependent
* Maximum slippage: instrument-dependent
* Maximum model uncertainty: configurable

These are provisional limits, not guarantees of maximum realized loss.

### Position sizing

Calculate position size from:

* Account equity
* Account currency
* Entry price
* Stop-loss distance
* Instrument pip or tick value
* Quote-to-account currency conversion
* Broker minimum trade size
* Broker unit precision
* Margin requirements
* Maximum permitted risk

Reject any position that cannot be sized within the specified restrictions.

### Mandatory protections

Implement:

* Daily loss circuit breaker
* Weekly loss circuit breaker
* Maximum drawdown monitoring
* Maximum consecutive-loss protection
* Correlated position monitoring
* Excessive spread protection
* Stale data protection
* Broker connection protection
* Abnormal volatility protection
* Duplicate order protection
* Unprotected-position detection
* Emergency trading suspension

Loss-limit calculations must consider relevant realized and unrealized exposure rather than relying only on closed trades.

Persist risk state across process restarts.

The system must fail closed when account state or broker execution state is uncertain.

---

# 14. AUTONOMOUS EXECUTION ENGINE

This is a critical component.

Implement a reliable broker execution architecture.

### Operating modes

Support three separate modes.

**Mode 1: SIGNAL_ONLY**

Generate signals and notifications.

Never place orders.

**Mode 2: PAPER**

Automatically simulate executions using realistic market prices, fees, spreads, and slippage.

Use a simulated portfolio.

**Mode 3: OANDA_PRACTICE**

Automatically execute and manage orders using an OANDA practice account.

**Mode 4: LIVE**

Design support for real-money trading.

LIVE mode must remain disabled by default.

Live trading must not become active through automatic configuration changes, deployment, or model retraining.

It must require an explicit, authenticated, auditable operator activation process.

Do not place live orders during development or testing.

### OANDA integration

Implement:

* Authentication
* Account retrieval
* Instrument information
* Pricing
* Historical candles
* Market orders
* Limit orders
* Stop orders where appropriate
* Stop-loss-on-fill
* Take-profit-on-fill
* Open trade retrieval
* Open order retrieval
* Transaction history
* Position monitoring
* Position closure
* Order cancellation
* Broker state reconciliation

Verify all order schemas against official current OANDA documentation.

### Execution safety

Every order must have a unique internal identifier.

Use broker-supported client identifiers where available.

Implement idempotent execution.

When an API request times out, do not blindly submit the same order again.

First reconcile the order state with the broker.

Maintain a durable order lifecycle:

PROPOSED → RISK_APPROVED → SUBMITTING → ACKNOWLEDGED → PENDING/FILLED → PARTIALLY_CLOSED/CLOSED/CANCELLED/REJECTED

Include additional states as necessary.

Every state transition must be logged.

Protective orders should be placed atomically with the entry through broker-supported order-on-fill functionality whenever available.

If an executed position unexpectedly lacks required protection, initiate the configured emergency response and alert the operator.

### Reconciliation

On application startup:

1. Retrieve broker account information.
2. Retrieve open orders.
3. Retrieve open positions.
4. Compare broker state against local database state.
5. Resolve known transactions.
6. Detect inconsistencies.
7. Prevent new entries until reconciliation succeeds.

Never assume the local database represents the broker's current state.

### Autonomous operation

Once a permitted execution mode is active, the system must automatically:

1. Monitor markets.
2. Generate candidate opportunities.
3. Evaluate probabilities.
4. Determine entry and exit prices.
5. Evaluate risk.
6. Submit qualifying orders.
7. Confirm execution.
8. Monitor positions.
9. Execute permitted trade-management actions.
10. Record outcomes.
11. Send Telegram notifications.

Normal operation must not require user confirmation for each paper or practice trade.

---

# 15. AUTOMATIC TRADE MANAGEMENT

Create a position-monitoring service.

It must monitor:

* Current market prices
* Open positions
* Unrealized P&L
* Broker-held protective orders
* Remaining position size
* Position duration
* Active strategy conditions
* Account-level risk exposure

Support configurable strategies such as:

* Fixed stop-loss and take-profit
* Time-based exit
* Trailing stop
* Break-even stop
* Partial profit-taking
* Strategy invalidation exit

Do not use unvalidated discretionary AI judgments to modify protective orders.

Trade-management rules must be deterministic, versioned, and tested.

Existing protective orders must remain effective if the application temporarily disconnects, subject to broker capabilities and normal execution risks.

---

# 16. DEEPSEEK AI REASONING ENGINE

Integrate the DeepSeek API.

Default model:

`deepseek-flash`

Make the provider configurable.

The LLM must receive structured, verified information from the quantitative engine.

### Responsibilities

The LLM may:

* Explain why a trading signal was generated.
* Summarize supporting technical indicators.
* Describe the market regime.
* Summarize verified financial news.
* Identify potential conflicts between market information and the signal.
* Explain why a trade was rejected.
* Generate readable performance summaries.
* Explain risk conditions.
* Produce trading journal narratives.

### Restrictions

The LLM must not:

* Invent market prices.
* Invent economic news.
* Fabricate confidence scores.
* Independently calculate executable position sizes.
* Independently execute broker orders.
* Modify account risk limits.
* Override the quantitative approval engine.
* Change stop-loss or take-profit levels without deterministic approval.
* Claim guaranteed profitability.

Use schema-validated structured outputs.

Treat external news and retrieved content as untrusted data.

Prevent prompt injection from causing system instructions, trade orders, or risk restrictions to change.

### Efficiency

Do not call the LLM for every market tick.

Use event-driven LLM analysis.

Trigger calls for:

* Newly approved trading opportunities
* Important trade updates
* Significant verified market events
* Completed trade explanations
* Performance reports

If DeepSeek is unavailable, the quantitative system must continue operating safely.

LLM outages must not prevent broker-side protective orders from functioning.

---

# 17. NEWS AND ECONOMIC EVENT FILTER

Design an optional economic-event awareness module.

Potential events include:

* Central bank interest rate announcements
* Inflation reports
* Employment reports
* Major scheduled economic releases
* Significant cryptocurrency-specific developments

Do not invent a news provider.

Create an adapter interface and configuration options for a legitimate economic calendar or news feed.

If no verified provider is configured, show the module as unavailable.

Never pretend live news monitoring is operating when it is not.

Initially implement configurable time-based restrictions around scheduled high-impact announcements when validated calendar data is available.

Use verified timestamps.

LLM summaries must reference the actual supplied event data.

---

# 18. TELEGRAM NOTIFICATION SYSTEM

Integrate the official Telegram Bot API.

The application must support:

* Bot connection testing
* Chat ID discovery
* Trade entry notifications
* Trade closure notifications
* Stop-loss notifications
* Take-profit notifications
* Trade rejection summaries
* Risk limit warnings
* Broker connection failures
* System startup notifications
* System shutdown notifications
* Daily trading summaries
* Weekly performance reports

### Example notification

**AEGISTRADE AI — TRADE EXECUTED**

Instrument: EUR/USD

Direction: LONG

Entry: 1.08500

Stop-loss: 1.08350

Take-profit 1: 1.08800

Take-profit 2: 1.08950

Risk/reward: 1:2 / 1:3

Model probability: 82%

Trading timeframe: 15 minutes

Position risk: 0.5%

Strategy: Trend continuation

Market regime: Bullish trend

Execution mode: OANDA PRACTICE

Status: FILLED

AI Explanation:

The quantitative model identified a potential trend continuation supported by momentum and market-structure features. The trade satisfied the configured probability, spread, and risk requirements.

The values above are illustrative placeholders only.

Actual notifications must contain verified system outputs.

### Notification reliability

Implement retries and delivery logging.

Prevent duplicate notifications.

Ensure Telegram failures cannot cause duplicate broker orders.

Implement notification deduplication using persistent event identifiers.

---

# 19. WEB DASHBOARD

Build a modern, responsive trading dashboard.

Use a clean professional financial trading interface.

A dark theme is preferred.

### Dashboard sections

**A. Overview**

Display:

* Trading mode
* Connection status
* Account equity
* Account balance
* Current P&L
* Daily P&L
* Weekly P&L
* Open positions
* Pending orders
* Recent signals
* Risk utilization

**B. Live Market Charts**

Provide:

* Candlestick charts
* Multiple timeframes
* Technical indicators
* Entry markers
* Stop-loss markers
* Take-profit markers
* Executed trade history
* Current market spread where available

**C. AI Trading Signals**

Display:

* Instrument
* Direction
* Entry
* Stop-loss
* Take-profit
* Expected return
* Estimated probability
* Strategy
* Market regime
* Approval or rejection status
* AI explanation

**D. Trade History**

Display:

* Executed trades
* Entry and exit timestamps
* Order status
* Entry and exit prices
* Realized profit/loss
* Trading costs
* Holding period
* Strategy
* Model version
* Reason for closure

**E. Strategy Analytics**

Display:

* Win rate
* Profit factor
* Expectancy
* Maximum drawdown
* Average reward/risk
* Performance by instrument
* Performance by timeframe
* Performance by strategy
* Performance by market regime

**F. Model Analytics**

Display:

* Current deployed model
* Model version
* Training period
* Testing period
* Confidence calibration
* Prediction distribution
* Recent model performance
* Performance deterioration warnings

**G. Risk Management**

Allow authorized users to view and configure supported risk limits.

The backend must independently validate every configuration change.

**H. System Health**

Show:

* Broker connectivity
* Data feed health
* Database connectivity
* Model loading status
* Telegram connectivity
* LLM availability
* Most recent market update
* Critical errors

### Dashboard security

Read-only access should be the default.

Authentication is required for administrative actions.

Do not expose live trading activation as an unauthenticated web endpoint.

---

# 20. BACKTESTING FRAMEWORK

Implement a professional historical backtesting engine.

The backtester must reuse the same strategy, prediction, trade approval, and risk-management logic as live operation wherever possible.

### Simulation requirements

Model:

* Historical bid/ask spreads
* Transaction costs
* Slippage
* Broker minimum order sizes
* Limit-order execution
* Stop-loss execution
* Take-profit execution
* Pending order expiration
* Market trading hours
* Financing costs where applicable
* Position sizing
* Margin constraints
* Partial fills where supported by the simulator
* Account-level risk limits
* Maximum simultaneous positions

Do not assume an order fills merely because a candle touches the entry level if the available data cannot justify that assumption.

For ambiguous intrabar sequences where both stop-loss and take-profit are touched, use conservative assumptions or higher-resolution data.

Report how the ambiguity was handled.

### Required performance metrics

Calculate:

* Total net return
* Annualized return where meaningful
* Maximum drawdown
* Win rate
* Profit factor
* Expectancy
* Sharpe ratio
* Sortino ratio
* Average winning trade
* Average losing trade
* Average holding period
* Trade frequency
* Average fees and slippage
* Exposure
* Risk-adjusted performance
* Consecutive losses
* Probability calibration

Provide equity curves and drawdown charts.

### Strategy comparisons

Compare candidate systems with:

* Simple baseline strategies
* Buy-and-hold where appropriate
* Naive directional models
* Individual trading strategies
* Combined models

Do not automatically conclude that the highest historical return indicates the best model.

Evaluate robustness, complexity, turnover, drawdowns, and performance across different market conditions.

Clearly distinguish:

* Training performance
* Validation performance
* Out-of-sample test performance
* Live paper-trading performance

---

# 21. CONTINUOUS PERFORMANCE EVALUATION

The system must maintain a complete history of generated trading opportunities.

Store:

* Approved signals
* Rejected signals
* Executed trades
* Unfilled orders
* Expired signals
* Model predictions
* Model versions
* Strategy versions
* Feature snapshots
* Actual outcomes
* Trading costs
* Risk decisions

Implement performance monitoring.

Detect:

* Declining predictive performance
* Poor confidence calibration
* Increased drawdown
* Excessive trading costs
* Changes in signal distributions
* Feature drift
* Market regime changes
* Strategy deterioration

The system should be able to suspend new trading when specified deterioration thresholds are exceeded.

---

# 22. AUTOMATED MODEL RETRAINING

Create a controlled model retraining pipeline.

Support:

* Scheduled training
* Updated historical datasets
* Data validation
* Feature computation
* Walk-forward validation
* Candidate model comparison
* Calibration
* Model versioning
* Evaluation reports

New models must not automatically replace active trading models solely because their training metrics improve.

Implement a model registry with statuses such as:

* EXPERIMENTAL
* VALIDATED
* SHADOW
* APPROVED
* ACTIVE
* RETIRED

A model must pass defined evaluation requirements before becoming eligible for deployment.

Require explicit operator approval for promotion into live trading.

Provide a rollback mechanism.

Retain previous working model versions.

---

# 23. DATABASE DESIGN

Create a normalized PostgreSQL schema.

Include tables or equivalent models for:

* instruments
* market_candles
* market_quotes
* data_ingestion_jobs
* strategies
* strategy_configurations
* model_versions
* model_training_runs
* model_evaluations
* market_regimes
* trade_signals
* signal_decisions
* orders
* order_events
* positions
* trades
* executions
* risk_events
* account_snapshots
* performance_metrics
* notification_events
* audit_logs
* system_health_events

Include:

* Appropriate foreign keys
* Unique constraints
* Indexes
* UTC timestamps
* Decimal-safe financial values
* Schema migrations
* Data retention controls

Financial order values must not rely on unsafe floating-point rounding.

Use Decimal and broker-defined precision where appropriate.

---

# 24. SECURITY REQUIREMENTS

Use environment variables for credentials.

Create `.env.example`.

Never hardcode API keys.

Required configuration includes:

```env
APP_NAME=AegisTrade AI
APP_ENV=development
LOG_LEVEL=INFO
TIMEZONE=America/Winnipeg

DATABASE_URL=postgresql://user:password@localhost:5432/aegistrade

OANDA_API_KEY=
OANDA_ACCOUNT_ID=
OANDA_ENVIRONMENT=practice

DEEPSEEK_API_KEY=
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-flash

OPENAI_API_KEY=

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

TRADING_MODE=paper
ENABLE_LIVE_TRADING=false

RISK_PER_TRADE=0.005
MAX_DAILY_LOSS=0.02
MAX_WEEKLY_LOSS=0.05
MAX_OPEN_POSITIONS=3

MIN_RISK_REWARD=2.0
INITIAL_PROBABILITY_THRESHOLD=0.80
```

Treat all values as configurable examples.

Use safe local defaults.

The actual `.env` file must be excluded from version control.

Use separate practice and live broker configurations.

Never display credentials in logs, traces, API responses, exceptions, or dashboard pages.

Implement:

* Authentication
* Role-based administrative permissions
* Secret redaction
* Input validation
* API timeouts
* Dependency vulnerability checks
* Secure exception handling
* Audit trails
* Safe configuration validation

---

# 25. RELIABILITY AND FAILURE RECOVERY

The system must operate safely during infrastructure failures.

Test scenarios including:

1. OANDA API outage.
2. Coinbase WebSocket disconnection.
3. DeepSeek API timeout.
4. Telegram API failure.
5. Database interruption.
6. Application restart during an active trade.
7. Duplicate market-data events.
8. Stale prices.
9. Rejected broker orders.
10. Partially filled orders.
11. Network timeout during order submission.
12. Unexpected open positions.
13. Invalid stop-loss calculations.
14. Insufficient account margin.
15. Missing model artifacts.
16. Trading outside permitted market hours.
17. Model prediction errors.
18. Severe volatility.
19. Unavailable economic-event data.
20. Corrupted or incomplete historical datasets.

Failures must not trigger unsafe order submission.

When necessary, stop opening new positions and generate an emergency alert.

---

# 26. PROJECT STRUCTURE

Create a maintainable repository structure similar to:

```text
aegistrade-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── market_data/
│   │   ├── indicators/
│   │   ├── strategies/
│   │   ├── regime_detection/
│   │   ├── machine_learning/
│   │   ├── backtesting/
│   │   ├── risk_management/
│   │   ├── trade_optimization/
│   │   ├── execution/
│   │   ├── brokers/
│   │   ├── llm/
│   │   ├── notifications/
│   │   ├── monitoring/
│   │   └── main.py
│   │
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── charts/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   └── package.json
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── samples/
│
├── model_artifacts/
│
├── scripts/
│
├── infrastructure/
│
├── docs/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── AGENTS.md
```

Adjust the structure when justified.

Avoid unnecessary abstractions.

Use shared interfaces where historical simulation and live trading require equivalent behaviour.

---

# 27. TESTING REQUIREMENTS

Use pytest and appropriate frontend testing tools.

Write:

* Unit tests
* Integration tests
* Data validation tests
* Feature calculation tests
* Backtesting tests
* Model evaluation tests
* Risk engine tests
* Broker adapter tests
* Order state machine tests
* Failure recovery tests
* API tests
* Frontend component tests
* End-to-end tests for essential workflows

### Critical invariants

Explicitly test that:

1. Live execution is impossible under default configuration.
2. Broker API calls cannot bypass the risk engine.
3. Missing or invalid stop-losses prevent entry.
4. Maximum position risk is enforced.
5. Daily and weekly loss limits prevent new entries.
6. Stale market data prevents new entries.
7. Duplicate signal events cannot create duplicate orders.
8. Network retries cannot blindly duplicate submissions.
9. Historical features never access future information.
10. Model evaluation preserves chronological integrity.
11. Rejected signals cannot reach the execution adapter.
12. LLM output cannot directly modify broker orders.
13. A restart triggers broker reconciliation before new entries.
14. Missing credentials produce actionable errors rather than application crashes.
15. Unavailable market data never results in fabricated prices.
16. Simulated trades use realistic bid/ask execution.
17. Order closure cannot unintentionally reverse a position.
18. Model retraining cannot silently replace the active live model.

Critical financial calculations require deterministic tests with known expected results.

---

# 28. LOCAL DEVELOPMENT AND DEPLOYMENT

The system must run locally using Docker Compose.

Provide services for:

* Backend API
* PostgreSQL
* Frontend
* Trading worker
* Market-data worker

Additional services may be introduced only when necessary.

Create startup health checks.

Provide commands for:

* Installing dependencies
* Initializing the database
* Running migrations
* Starting the application
* Downloading historical data
* Training models
* Running backtests
* Starting paper trading
* Connecting to OANDA practice
* Running automated tests
* Viewing logs

The application must have a useful offline demonstration mode using clearly labeled fixture data.

Do not require paid APIs simply to run the test suite.

Prepare deployment documentation for a future AWS installation.

Do not deploy or enable live trading automatically.

---

# 29. DEVELOPMENT PHASES

Build the application incrementally.

Do not attempt to implement every component as one enormous, untested code change.

Each phase must deliver working code.

## PHASE 1 — FOUNDATION

Implement:

* Repository structure
* Python backend
* PostgreSQL
* Docker Compose
* Configuration management
* Logging
* Health endpoints
* Database migrations
* Basic frontend
* Initial automated tests

Acceptance criteria:

The application starts locally and the health endpoints respond successfully.

## PHASE 2 — MARKET DATA

Implement:

* OANDA historical data adapter
* Coinbase historical data adapter
* Market data normalization
* Local data storage
* Data quality checks
* Live price ingestion
* Reconnection logic

Acceptance criteria:

Historical and live data can be ingested, validated, and queried.

The pipeline works with offline fixtures and can connect to configured providers.

## PHASE 3 — QUANTITATIVE STRATEGIES

Implement:

* Indicator engine
* Strategy framework
* Trend strategy
* Momentum strategy
* Breakout strategy
* Mean reversion strategy
* Market structure analysis
* Regime detection

Acceptance criteria:

Strategies generate reproducible candidate signals using historical data without look-ahead bias.

## PHASE 4 — BACKTESTING

Implement:

* Trade simulator
* Execution assumptions
* Spread and slippage
* Portfolio accounting
* Position sizing
* Risk rules
* Performance reports

Acceptance criteria:

A historical backtest produces reproducible results and passes execution edge-case tests.

## PHASE 5 — MACHINE LEARNING

Implement:

* Feature engineering
* Label generation
* Model training
* Walk-forward validation
* Hyperparameter optimization
* Calibration
* Model registry
* Model evaluation reports

Acceptance criteria:

Models train successfully, generate calibrated probability estimates where supported by evidence, and produce reproducible evaluation reports.

If no model demonstrates an advantage, report the failure rather than fabricate acceptable performance.

## PHASE 6 — TRADE OPTIMIZATION

Implement:

* Entry optimization
* Stop-loss engine
* Take-profit engine
* Expected value calculation
* Trade approval engine
* Signal expiration

Acceptance criteria:

Every approved signal has valid entry, stop-loss, take-profit, position size, and documented risk.

## PHASE 7 — AUTONOMOUS PAPER TRADING

Implement:

* Event-driven trading worker
* Paper execution adapter
* Order state machine
* Position monitoring
* Trade journal
* Automatic exit management
* Portfolio risk monitoring

Acceptance criteria:

The system autonomously opens, monitors, and closes simulated positions without manual intervention.

## PHASE 8 — OANDA PRACTICE EXECUTION

Implement:

* Practice API authentication
* Order execution
* Stop-loss-on-fill
* Take-profit-on-fill
* Broker reconciliation
* Position monitoring
* Failure handling

Acceptance criteria:

With valid practice credentials supplied by the operator, the platform can autonomously execute and manage practice-account positions.

All critical broker integration tests must pass.

## PHASE 9 — LLM AND TELEGRAM

Implement:

* DeepSeek integration
* Structured AI explanations
* Optional provider switching
* Telegram notifications
* Trade summaries
* Failure alerts

Acceptance criteria:

Executed practice or simulated trades generate accurate notifications using actual system data.

## PHASE 10 — FULL DASHBOARD

Implement:

* Account overview
* Live charts
* Signals
* Trade history
* Model analytics
* Performance dashboards
* Risk monitoring
* System health

Acceptance criteria:

The dashboard accurately reflects the database and current trading-engine state.

## PHASE 11 — HARDENING

Implement:

* Extended automated testing
* Crash recovery
* Operational monitoring
* Security improvements
* Deployment scripts
* Model drift monitoring
* Detailed documentation

Acceptance criteria:

The system safely handles the specified failure scenarios and has reproducible operating procedures.

## PHASE 12 — LIVE EXECUTION READINESS

Design and document:

* Separate live credentials
* Live account validation
* Operator authorization
* Live activation workflow
* Portfolio-level safety controls
* Deployment procedures
* Emergency shutdown
* Operational monitoring
* Incident recovery

Do not activate real-money trading.

Do not claim the system is ready for real-money operation based solely on successful software tests.

Provide a readiness report identifying outstanding operational, regulatory, strategy-validation, and execution risks.

---

# 30. PERFORMANCE AND MODEL ACCEPTANCE

Do not define success solely as achieving a high win rate.

Evaluate:

* Positive net expected value
* Out-of-sample profitability
* Profit factor
* Drawdown
* Calibration
* Risk-adjusted returns
* Trading frequency
* Stability across market regimes
* Stability across validation periods
* Execution sensitivity
* Trading cost sensitivity

Establish explicit numerical acceptance criteria using validation research and documented risk preferences.

Avoid selecting those criteria after viewing final test results.

A model that achieves 85% directional accuracy but loses money after costs must be rejected.

A model with lower accuracy but demonstrably stronger risk-adjusted returns may be preferable.

Report uncertainty and confidence intervals where appropriate.

Do not present a short profitable backtest as proof that a strategy will continue to work.

If the research does not establish an advantage, retain the system in research or paper mode and explain why.

---

# 31. REQUIRED DOCUMENTATION

Create:

**README.md**

Project overview, installation, configuration, startup, and testing.

**ARCHITECTURE.md**

System architecture and major component responsibilities.

**DATA_PIPELINE.md**

Data providers, ingestion process, storage, and data quality.

**TRADING_STRATEGIES.md**

Implemented strategies, assumptions, and validation.

**MODEL_TRAINING.md**

Feature engineering, training, calibration, validation, and model management.

**BACKTESTING.md**

Execution assumptions, methodology, known limitations, and performance interpretation.

**RISK_MANAGEMENT.md**

Risk calculations, restrictions, and emergency procedures.

**BROKER_INTEGRATION.md**

OANDA integration and supported execution capabilities.

**OPERATIONS.md**

System startup, shutdown, recovery, monitoring, and troubleshooting.

**SECURITY.md**

Credential handling and administrative security.

**LIVE_TRADING_READINESS.md**

Operational requirements before live activation.

**CODEX_PROGRESS.md**

Current development phase, completed work, tests, blockers, and remaining tasks.

---

# 32. CODEX EXECUTION INSTRUCTIONS

You are responsible for implementing this project.

Follow these instructions carefully.

### Step 1

Inspect the repository and development environment.

Determine whether any existing code should be preserved.

### Step 2

Create an implementation plan organized around the development phases above.

Identify dependencies between components.

### Step 3

Begin implementation immediately.

Do not stop after generating the plan.

### Step 4

Implement one working component at a time.

Use appropriate interfaces so components can be integrated without major rewrites.

### Step 5

After each significant implementation step:

1. Run appropriate tests.
2. Fix errors.
3. Verify imports.
4. Verify application startup.
5. Confirm the component integrates with the existing system.
6. Update CODEX_PROGRESS.md.

### Step 6

Continue through the development phases as the available execution environment permits.

Do not repeatedly ask for confirmation of already-defined technical decisions.

Choose reasonable, well-documented defaults.

Ask for user input only when an external credential, irreversible action, legally significant decision, or other genuinely necessary item cannot be resolved safely.

### Step 7

When credentials are missing, use environment variables, mock adapters, and offline test data.

Do not block the entire project because an API credential has not yet been configured.

### Step 8

Do not substitute mock integrations for real implementations without clearly identifying them.

Maintain a distinction between:

* Fully implemented and tested
* Implemented but awaiting external integration verification
* Mocked
* Incomplete
* Unsupported

### Step 9

Do not make up successful test results.

Only report tests that actually executed.

### Step 10

When an implementation phase is complete, proceed to the next dependent phase.

If execution constraints require stopping, leave the repository in a working state and update CODEX_PROGRESS.md with exact remaining tasks and a clear continuation point.

---

# 33. FINAL DELIVERY REQUIREMENTS

The completed project should contain:

1. Functional FastAPI backend.
2. Functional React dashboard.
3. Historical Forex data ingestion.
4. Historical cryptocurrency data ingestion.
5. Live market-data integration.
6. Technical indicator engine.
7. Multiple quantitative trading strategies.
8. Market regime analysis.
9. Machine learning training pipeline.
10. Out-of-sample validation.
11. Calibrated probability estimates.
12. Entry optimization.
13. Stop-loss calculation.
14. Take-profit calculation.
15. Position sizing.
16. Expected value evaluation.
17. Deterministic risk management.
18. Autonomous paper-trading engine.
19. OANDA practice execution.
20. Broker position reconciliation.
21. Position monitoring.
22. Trade performance journal.
23. DeepSeek AI explanations.
24. Telegram notifications.
25. Model monitoring.
26. Controlled retraining.
27. Automated tests.
28. Docker deployment configuration.
29. Complete setup documentation.
30. Live-trading readiness procedures.

At the end of each development session, provide:

* Components implemented
* Files created or modified
* Tests executed and results
* Known limitations
* Remaining blockers
* Current implementation phase
* Exact commands required to run the application
* Recommended next development task

Do not claim the entire platform is complete unless all required acceptance criteria have been satisfied.

---

# 34. ULTIMATE SYSTEM BEHAVIOUR

The final target is a fully autonomous trading intelligence system.

Once initialized in an authorized execution mode, it should:

1. Connect to market-data providers.
2. Collect and validate current prices.
3. Update relevant market features.
4. Determine current market conditions.
5. Evaluate eligible trading strategies.
6. Run trained machine learning models.
7. Estimate calibrated outcome probabilities.
8. Identify potential entry opportunities.
9. Determine valid stop-loss levels.
10. Determine profit targets.
11. Calculate potential reward and risk.
12. Evaluate expected profitability after costs.
13. Check account-level exposure.
14. Enforce all configured restrictions.
15. Reject unsuitable opportunities.
16. Automatically execute qualifying trades in the authorized environment.
17. Confirm broker execution.
18. Monitor active positions.
19. Manage positions according to predefined policies.
20. Record completed trades.
21. Update performance analytics.
22. Generate DeepSeek explanations.
23. Send Telegram notifications.
24. Monitor model performance.
25. Suspend new trading when safety conditions are violated.

The system must remain capable of deciding not to trade.

Its success must be measured through verified net trading performance, risk-adjusted returns, reliability, and safety—not the number of signals generated.

**Primary engineering priority: Build a trustworthy, statistically testable, risk-controlled autonomous trading system rather than a trading bot that merely produces convincing predictions.**

---

# BEGIN IMPLEMENTATION

Start by inspecting the current repository.

Then:

1. Create the architecture and implementation plan.
2. Initialize the project structure.
3. Implement the backend foundation.
4. Configure the database and Docker environment.
5. Begin building the market-data ingestion pipeline.
6. Add automated tests immediately.
7. Continue implementing dependent phases as working code.

Do not stop at planning.

Do not enable real-money trading.

Make the application runnable and verifiable at every development milestone.

Begin now.
