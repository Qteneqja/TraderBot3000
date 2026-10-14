# Development rules

Read Prompt.md and CODEX_PROGRESS.md before continuing implementation. Preserve truthful status distinctions: tested, externally unverified, mocked, incomplete and unsupported.

- Real-money execution remains unsupported. Never remove gates to make a demonstration trade.
- Use Decimal for financial values and explicit broker precision. Do not invent prices or probabilities.
- Every entry must pass deterministic risk checks and durable idempotency/reconciliation.
- Keep fixture data separate from provider data. No secret values in logs, snapshots, frontend or commits.
- Future candles and overlapping label windows must not leak into model/strategy decisions.
- Training cannot promote a model. LLM narratives cannot mutate execution or risk state.
- Run relevant pytest tests, frontend tests/build, and migration checks after changes; document actual results.
- Before enabling practice submission, complete the acceptance items in docs/BROKER_INTEGRATION.md.

Local commands and Docker instructions are in README.md. The tests require no paid provider access.
