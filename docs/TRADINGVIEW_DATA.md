# TradingView history diagnostic

On October 14, 2026, an isolated Windows Python 3.13 environment successfully
installed tvdatafeed 2.1.0 from upstream commit
`e6f6aaa7de439ac6e454d9b26d2760ded8dc4923`. Anonymous requests returned:

| TradingView symbol | Interval | Requested/received | Calendar span |
| --- | --- | --- | --- |
| NSE:NIFTY | 1 hour | 1,000/1,000 | 223 days |
| OANDA:EURUSD | 5 minutes | 5,000/5,000 | 23.36 days |
| COINBASE:BTCUSD | 5 minutes | 5,000/5,000 | 17.36 days |

All three frames were ordered, with zero duplicate timestamps and zero missing
cells. These checks establish retrieval only. They do not establish candle
completeness, correct UTC conversion, price accuracy or suitability for execution.
No downloaded rows were imported into the application database or used to train
or activate a model. NIFTY is outside the bot's configured markets.

## Reproduce

Run from the repository root. This separate environment is under an ignored
research directory; the production dependency lock and running services are unchanged.

```powershell
.venv/Scripts/python.exe -m venv data/raw/tvdatafeed-probe-env
data/raw/tvdatafeed-probe-env/Scripts/python.exe -m pip install --no-cache-dir "git+https://github.com/rongardF/tvdatafeed.git@e6f6aaa7de439ac6e454d9b26d2760ded8dc4923" python-dotenv==1.2.4
data/raw/tvdatafeed-probe-env/Scripts/python.exe scripts/probe_tradingview.py
```

Observed dependencies included pandas 3.0.6, numpy 2.5.4, websocket-client 1.9.2
and requests 2.34.2. This is an optional diagnostic environment, not a locked
production integration. Each request runs in a separate process with a 45-second
deadline. Output is metadata only; third-party logs and exception messages are
suppressed to avoid exposing remote headers or tokens. Inspect the JSON status;
the probe continues to the next symbol after a failure.

Optional authentication reads only `TRADINGVIEW_USERNAME` and
`TRADINGVIEW_PASSWORD` from the ignored root `.env` (or process environment).
Enter these locally, never in source files, terminal arguments or commits. Then run:

```powershell
data/raw/tvdatafeed-probe-env/Scripts/python.exe scripts/probe_tradingview.py --login
```

The probe reports `AUTHENTICATION_FAILED` if upstream silently falls back to
anonymous mode. Authenticated access has not yet been externally verified.

## Suitability for this bot

The [upstream README](https://github.com/rongardF/tvdatafeed) documents up to
5,000 bars. The inspected `get_hist` implementation exposes no historical
start/end pagination. The returned five-minute samples therefore cannot meet
the current research policy's 180-calendar-day minimum. Login alone is not
evidence of deeper history. Hourly NIFTY data cannot substitute for the supported
five-minute Forex/crypto deployment contract.

The inspected parser converts timestamps using host-local `datetime.fromtimestamp`
and returns naive datetimes; it parses prices as floats and can replace missing
volume with zero. It returns no bid/ask components or completed-candle indicator.
Any future importer must preserve TradingView provenance separately, normalize
and validate timestamps, exclude open bars, handle Decimal precision explicitly,
and distinguish missing volume from genuine zero. It must not label these rows
as directly downloaded OANDA/Coinbase data or bypass the provider acceptance gate.

The existing direct OANDA and Coinbase adapters remain the historical backfill
path for model research. TradingView is a demonstrated supplementary retrieval
option; a validated ingestion adapter and deployment eligibility are not implemented.
