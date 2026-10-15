# Autonomous trading readiness

2026-10-15 UTC checkpoint: the platform is **not qualified for autonomous trading**. Engineering tests are passing; predictive/economic evidence is insufficient. No gate was removed to produce activity.

| Area | Measured status |
| --- | --- |
| Runtime | Seven local services healthy after rollout at 22:44 UTC; all four worker heartbeats fresh; schema 0011 and HTTP smoke pass |
| Research | Four-asset/six-strategy outcome diagnostics, 19 compatible artifacts, 57 metadata records, 20 declared entry/horizon comparisons complete |
| New model training | Two isolated diagnostic BTC LightGBM repetitions only; no new production registry candidates |
| Native crash | Bounded reproduction passed; original -11 cause remains unresolved |
| Calibration | All 19 matched calibrated Brier/log-loss pairs improve on raw; no calibrated .80 candidate evidence |
| Costs | Current CAD account terms partly observed; commission/historical financing/conversion/fill costs unverified |
| Activation | No eligible model; zero active PAPER deployments |
| Future evaluation | No reservation; 45-day-plus-horizon observation not started |
| PAPER | Infrastructure recorder RUNNING; no actual orders, no formal performance trial |
| OANDA practice | Read-only checks pass; no submissions; acceptance and explicit authorization outstanding |
| Telegram | One confirmed connection test; no genuine trade messages; new monitoring commands tested with mocks and disabled by default |
| LLM | Existing bounded sanitized DeepSeek narrative permission retained; no expansion to news/raw datasets or execution authority |
| Real-money / crypto execution | Unsupported |

The qualification path is: obtain independent execution-cost evidence; preregister a defensible sufficiently populated causal strategy experiment; pass unchanged validation/walk-forward/base/stress requirements; freeze and reserve a genuinely future final test; wait at least 45 days plus full outcome horizon; evaluate once; explicitly approve eligible PAPER activation; complete the genuine elapsed formal PAPER trial; then complete broker lifecycle acceptance and obtain the required practice submission authorization. Training and LLM narratives cannot skip any step.

This session establishes negative and sparse research results rather than a market edge. Larger models, a lower threshold, an illustrative trade or estimated fees presented as verified would not remedy the missing evidence. Limit entries, adaptive trailing execution, optional news intelligence, richer operational alert producers and sustained recovery soak remain incomplete; they must receive their own execution/cost/causality acceptance before claims of support.

## External architecture review

Reviewed the public README architecture of [Opselon/NexusTradingForexBot](https://github.com/Opselon/NexusTradingForexBot): causal feature processing, TCN/attention research, separate risk/execution layers, shadow mode and governed promotion are relevant design patterns. Its XAUUSD/MT5 context and architecture do not establish transferable EUR/USD, GBP/USD or crypto alpha. No external implementation was copied or executed; this is a bounded documentation review, not a code audit. Deep learning is deferred until it has a justified hypothesis, sufficient independent observations and a predeclared fair baseline comparison.

Reviewed [Opselon/ForexTradingBot](https://github.com/Opselon/ForexTradingBot) documentation for Telegram/RSS organization. The useful separation is monitoring/news presentation from decision and execution state. The new monitoring commands retain this application's durable outbox and have no trading authority. RSS/news integration is optional, remains unconfigured, and must not silently expand approved LLM data sharing. Public claims of signal precision/automatic forwarding were not adopted as evidence or execution design.

## Verify and continue

```powershell
git status --short
git log -3 --oneline
docker compose ps
docker compose exec backend alembic current
docker compose exec backend alembic check
docker compose exec backend python -m app.cli activation-diagnostic
.venv/Scripts/python.exe scripts/verify_stack.py
```

See [root causes](MODEL_ROOT_CAUSE_ANALYSIS.md), [strategy comparison](STRATEGY_COMPARISON.md), [experiment identities](RESEARCH_EXPERIMENT_REGISTRY.md), [costs](EXECUTION_COST_VALIDATION.md), [qualification](MODEL_QUALIFICATION_REPORT.md), [prospective status](PROSPECTIVE_EVALUATION_STATUS.md), [PAPER evidence](PAPER_TRADING_EVIDENCE.md), [practice acceptance](OANDA_PRACTICE_ACCEPTANCE.md), and [Telegram evidence](TELEGRAM_DELIVERY_EVIDENCE.md). Exact verification results and the continuation point are in `CODEX_PROGRESS.md`.
