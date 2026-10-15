# Telegram delivery and evidence

The ignored `.env` supplies `TELEGRAM_BOT_TOKEN`, the numeric destination `TELEGRAM_CHAT_ID`, and `ENABLE_NOTIFICATIONS`. A bot username identifies the bot; it is not the private recipient's numeric chat ID. Open the bot and send Start before checking access. Do not commit credentials or private chat metadata.

One real connectivity message was explicitly approved and API-confirmed on October 15, 2026, around 17:25 UTC. The initial recipient name returned HTTP 400/chat-not-found. An explicitly approved metadata-only lookup verified the named bot and one recent private chat, then updated only the ignored recipient setting. No message contents were displayed. This receipt verifies the bounded API send, not that a human read it, future availability or a real trading lifecycle. No second test message was sent.

Automatic delivery was subsequently enabled for the requested future confirmed execution events. The outbox then contained only the delivered test receipt and no pending messages. Execution authorization remains independent. Zero paper/practice orders means there are no actual fill/closure delivery results yet.

## Operator test

Only use `--send` when the operator explicitly authorizes a connectivity message. A stable event identifier prevents duplicate sends and cannot reset FAILED/UNKNOWN evidence. The command checks bot authentication and chat access before inserting one test event, then delivers only that event; it does not drain trading notifications or claim that execution is operational.

```powershell
# Read status only; does not send:
docker compose exec backend python -m app.cli telegram-test --event-id NEW_TEST_ID --operator local-operator
# Only after explicit approval for that test message:
docker compose exec backend python -m app.cli telegram-test --event-id NEW_TEST_ID --operator local-operator --send
```

Confirmed delivery requires HTTP success, `ok=true`, a positive message ID, and a matching numeric destination in the receipt. Raw responses, URLs containing tokens and chat IDs are excluded from health responses and audit summaries. PAPER notifications state internal simulation; practice notifications use recorded broker lifecycle fields and distinguish quarantine from confirmed execution. LLM prose does not authorize or certify a trade.

Migration 0010 adds claim/delivery/retry times and safe error codes. Legacy timestamps stay unknown and old boolean delivery rows without receipts do not prove the new confirmation protocol. Claims commit before egress. Two senders cannot claim the same pending event. A valid explicit rate-limit rejection can retry after Telegram's deadline, at most five attempts; transport ambiguity, malformed success, server uncertainty or interruption becomes UNKNOWN without blind retry. Stale responses cannot overwrite quarantine. The connectivity test never schedules an automatic retry after its single authorized attempt.

`GET /api/notifications` and the activation diagnostic expose actual counts, latest attempt/error code, historical preflight failure and receipt evidence. Configured credentials alone are not delivery proof; disabled automatic dispatch remains distinct from a successful connection test. Existing trade-event outbox entries are committed with their order transitions, so failed notifications cannot roll back or duplicate orders.

Current boundaries: PAPER/practice filled/closed events and approved drift-suspension alerts are integrated. The complete requested catalog of operational alerts, daily summaries, pending/partial-order events and broker limit/stop orders is not implemented. Those must not be described as verified delivery. Delivery receipts do not establish an exactly-once guarantee at Telegram after an ambiguous network failure; the system chooses quarantine instead of a potentially duplicated send.

Protocol checked against the official [Bot API methods and responses](https://core.telegram.org/bots/api) and [sendMessage](https://core.telegram.org/bots/api#sendmessage). Never enable provider debug logging that prints credential-bearing URLs.

## Read-only monitoring

`ENABLE_TELEGRAM_MONITORING=false` defaults off. After migration 0011, the trading
worker can poll `/status`, `/models`, `/positions`, `/trades`, `/performance`,
`/signals`, `/risk`, `/news` from the configured numeric private recipient only.
First enable discards old updates; replies use the existing durable outbox.
Run only one application/consumer for a bot's getUpdates queue. No command can
activate a model, change risk or submit an order. `/news` reports unconfigured.
See [delivery evidence and limitations](TELEGRAM_DELIVERY_EVIDENCE.md).
