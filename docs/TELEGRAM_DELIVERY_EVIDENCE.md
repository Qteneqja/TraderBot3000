# Telegram delivery and monitoring evidence

As of 2026-10-15 UTC: one earlier explicitly authorized connectivity test has an API-confirmed delivery receipt. Automatic trade-event delivery is enabled. Genuine paper trade notifications: **0**; broker-confirmed practice trade notifications: **0**, because no trades exist. This session sent no new test message or research summary through Telegram. A connectivity receipt is not genuine trade-delivery evidence.

The existing durable outbox remains authoritative: claim-fenced sends, exact configured numeric-chat receipt validation, bounded safe 429 retry, interrupted/ambiguous sends quarantined UNKNOWN, and no blind uncertain-delivery replay. PAPER/practice fill and closure producers remain tied to actual confirmed states; fixture test messages must remain clearly identified. No fabricated execution was used to exercise delivery.

New read-only commands are implemented behind `ENABLE_TELEGRAM_MONITORING=false` by default:

`/status`, `/models`, `/positions`, `/trades`, `/performance`, `/signals`, `/risk`, `/news`.

They support exact commands without arguments or bot suffixes from the configured positive numeric **private** recipient only, with matching non-bot sender identity. No group, edited/channel/forwarded authority, arbitrary command execution, model activation, risk mutation or broker call is provided. The news reply explicitly reports that news monitoring is unconfigured. Provider PAPER order aggregates exclude fixtures; practice remains separately labeled CAD. Missing evidence is reported UNKNOWN or unverified.

Schema 0011 adds a durable opaque recipient/bot-bound cursor. First enable discards pre-existing updates. Cursor advancement and reply intentions commit atomically; replayed/stale updates cannot enqueue duplicate replies. Reply text uses bounded allowlisted aggregates and never stores incoming message text, tokens, chat/account IDs, balances or raw payloads. The existing outbox then delivers responses and verifies receipts. Monitoring remains disabled in this session; external polling/reply delivery is **UNVERIFIED**. It must not be enabled alongside another consumer of the same bot's `getUpdates` queue.

Mocked tests cover bootstrap, unauthorized recipients/senders/groups, forbidden activation commands, replay, invalid sequence, disabled configuration, reply-format rollback and lack of execution/risk mutations. Live command receipts and concurrency/recovery soak evidence remain outstanding. Additional online/model-qualified/outage/recovery/trial/daily/weekly alert producers are not all implemented; existing trade messages and status commands must not be described as completing that broader milestone.

See [Telegram operations](TELEGRAM.md) for the existing connectivity workflow. Do not repeat its external test merely to create more receipts. Enabling monitoring is separate from enabling orders and cannot award execution authority.
