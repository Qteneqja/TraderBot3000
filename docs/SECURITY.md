# Security

Credentials come from environment variables and use SecretStr where appropriate. `.env`, databases and model artifacts are ignored. Docker contexts exclude secrets; frontend bundles contain none. API reports configuration status without exposing keys. Avoid logging authorization headers or Telegram URLs.

Read-only dashboard and loopback binding are defaults. Suspension uses constant-time bearer comparison and is unavailable without ADMIN_TOKEN. There is no live activation endpoint. Internet deployment authentication, roles, sessions and rate limits remain incomplete: do not publicly expose this local stack.

Nginx sends a restrictive content policy, frame denial and content-type protection. React renders narratives as text. LLM inputs are untrusted data; schema-checked output has no broker/risk capability. Missing providers return unavailable explanations.

The default narrative adapter uses [DeepSeek chat completions](https://api-docs.deepseek.com/api/create-chat-completion/) with configurable `deepseek-flash`. Optional OpenAI-compatible transport requires an appropriate explicit model. No external LLM or Telegram messages were sent during development. Event-driven integration is incomplete.

Telegram event IDs are persistent. Ambiguous delivery becomes UNKNOWN, never blindly retried. Exactly-once Telegram delivery cannot be assumed. Multi-worker outbox leasing, connection/chat discovery, scheduling and Retry-After handling remain outstanding.

Joblib is executable serialization: load only trusted artifacts. Shadow loading confines filenames to the configured directory, checks the checksum before deserialization, and compares embedded metadata, features, event definition and classes. Registry and artifact directory remain trusted operator resources; hashes are not signatures. Paper-trial activation requires a verified review and an explicit local CLI action with operator/reason audit fields. These labels are not authenticated user identity. The deployment contract is rechecked on inference; there is no deployment write API or broker activation route. Dependency lockfiles improve reproducibility; a formal security audit is still required.
