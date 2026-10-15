# PAPER evidence

Checked 2026-10-15 UTC. Mode PAPER, provider data enabled, real-money execution disabled/unsupported. Active PAPER deployments: **0**. Actual stored paper orders: **0**; open/closed paper positions: **0/0**. No realized trading P&L exists; this is absence of trades, not a return estimate.

Recorder `830f86ec-8a53-467d-a9c1-f1a65ffbce29` is RUNNING as an infrastructure recorder. It observes worker/feed/decision behavior and remains separate from a qualified model performance trial. Previous stopped recorder `786fcdcc-dfd3-4039-9246-9feb4def1c69` is preserved. Historical fixture candles and fixture signal records remain segregated from provider research.

Durable PAPER idempotency, risk locking, activation/rollback, exits, fees, financing and recovery have automated test coverage. Positive eligibility in orchestration tests is explicitly mocked. None of those tests constitutes an actual model performance trial or proof of edge. See [trial methodology](PAPER_TRIALS.md).

The formal trial has not begun. It still requires an eligible, explicitly approved model and frozen policy, then genuine elapsed evidence: at least 30 wall days, 20 observed days, 100 closed trades and 20 active days, together with the binding return/risk/calibration requirements. Accelerated fixture replay and zero-exposure recordings cannot satisfy it. Do not fabricate a demonstration trade to populate the journal.

Read-only verification:

```powershell
docker compose exec backend python -m app.cli activation-diagnostic
.venv/Scripts/python.exe scripts/verify_stack.py
```
