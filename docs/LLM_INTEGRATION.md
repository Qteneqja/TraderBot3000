# DeepSeek commentary and quantitative training

DeepSeek is an event-driven explanation layer. Quantitative CPU models train on provider candles; API explanation requests do not fine-tune DeepSeek. LLM text is not a label, probability, model-selection instruction, risk input, activation command or broker order. No trading component reads narrative output.

Migration 0009 adds narrative_records. The separate llm-worker scans terminal research jobs and recorded PAPER/practice fills/closes. It builds an allowlisted snapshot directly from stored records, excluding credentials, account identifiers/balances, broker IDs, raw requests, arbitrary free-form messages and untouched final-test results. Research payloads contain asset/provider/strategy, validation Brier/calibration, simulated portfolio metrics and explicit limitations. Trade payloads contain recorded direction, entry/exit, fees/net P&L and fixture/PAPER/practice classification. Sharing trade summaries is external data sharing even when identifiers are excluded; review and authorize the scope before enabling.

Default ENABLE_LLM_NARRATIVES=false makes no LLM requests. Once authorized, local settings allow at most four attempts per UTC day, at least sixty seconds apart, with seven hundred output tokens and a twenty-second timeout. Concurrent workers share the durable budget lock; no network call runs while holding account/risk locks. These controls bound attempts and tokens, not a guaranteed currency cost. No Telegram message is sent by this integration.

Requests use the official DeepSeek chat endpoint with the configured deepseek-flash model, JSON-object output and thinking explicitly disabled. The [official API reference](https://api-docs.deepseek.com/api/create-chat-completion/) documents these fields, including the need to request JSON in the prompt and detect truncated output. No tool definitions or executable actions are supplied. Redirects are disabled.

Responses must match exactly summary, risks and limitations; extra execution fields/tool calls, oversized or malformed JSON, incomplete finish states, configured secrets and numeric narrative claims are rejected. Recorded numerical facts remain authoritative and separate. Natural-language commentary can still be wrong; the dashboard labels it untrusted and grants it no authority. React renders it as escaped text rather than executing HTML or commands.

Idempotent event IDs, snapshot/prompt hashes and REQUESTING committed before POST prevent duplicate cost on ordinary polling. Timeout/network interruption becomes UNKNOWN; provider/validation errors become FAILED. No automatic retry of ambiguous or failed records occurs. After a restart, old in-flight requests are quarantined; stale processes cannot overwrite that decision. A successful response establishes that one bounded call worked, not continuous availability or strategy profitability. Health remains independent from the trading worker.

```powershell
# Requires authorized ENABLE_LLM_NARRATIVES=true; otherwise makes no external call.
docker compose exec backend python -m app.cli llm-tick
```

The read-only /api/narratives and AI commentary panel expose source classification, validated explanation/error state and request limits. /api/system reports DISABLED, NOT_CONFIGURED, AWAITING_FIRST_RESPONSE, SUCCEEDED, FAILED, UNKNOWN or stale-success status from actual records. No HTTP endpoint enables requests or executes arbitrary snapshots.

October 15 verification: mocked provider tests cover JSON/truncation/tool/secret/numeric/oversized rejection, missing credentials, request idempotency, concurrent budget claims, UTC daily rollover, tamper detection, timeout/restart quarantine and stale results, with unchanged models/orders/account state on SQLite and PostgreSQL. Actual DeepSeek verification is pending explicit external-sharing approval: automatic review rejected the initial enable/deploy attempt because payload egress was not specifically authorized. No request was sent by that attempt. The exact research preview is saved locally in ignored data/reports/deepseek-payload-preview-20261015.json. Local flag remains false while approval is pending.

Training has independently begun: eight new weekly provider-data plans cover momentum and mean reversion for EUR_USD, GBP_USD, BTC-USD and ETH-USD, each comparing logistic, Random Forest, LightGBM and XGBoost (thirty-two additional planned candidates). Existing four trend schedules remain. Costs and original safety thresholds are unchanged; all runs are validation-only, honor reserved future holdouts and never activate models. Provider errors, insufficient samples and poor results are retained rather than suppressed. No promise of a qualifying strategy is made.
