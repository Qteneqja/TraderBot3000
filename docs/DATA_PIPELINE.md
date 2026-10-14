# Data pipeline

OANDA uses practice `/v3/instruments/{instrument}/candles`, `price=MBA`, and pages below 5,000 bars. Bid/ask OHLC and tick-volume provenance are retained. Coinbase uses public `/api/v3/brokerage/market/products/{product_id}/candles` in 300-bar windows. Crypto traded-base volume is not equated with Forex tick counts.

UTC timestamps, interval alignment, finite positive OHLC, coherent ranges and nonnegative volume are required. Incomplete/future, duplicate and out-of-order batches are rejected. Database unique keys make reingestion idempotent. Page data and resume cursor commit atomically. Failed jobs retain the previous committed cursor. Jobs currently retain the last page quality report, not all page reports.

Quotes reject crossed, stale/future timestamps; conditional upserts reject older events. OANDA pricing and Coinbase heartbeat/ticker streams use read timeouts and bounded exponential reconnection. Completed candles are REST-polled. Tick-derived candle construction and sequence-gap recovery remain incomplete.

Gaps are classified `unverified_closure_or_missing_data`; no bars are invented. Verified Forex calendars/holiday schedules remain outstanding. Strategies require a contiguous 60-bar warm-up after a gap. Downloaded bars are never automatically declared execution-quality. Parquet export uses zstd compression. Multi-year capacity tests and retention/compaction remain outstanding.

Synthetic fixtures have source `fixture`, deterministic generation, January 2025 timestamps and explicit UI labels. They are never substituted for missing provider data.

Official references: [OANDA instrument endpoints](https://developer.oanda.com/rest-live-v20/instrument-ep/), [Coinbase public candles](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/get-public-product-candles), [Coinbase streams](https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/websocket/websocket-endpoints).
