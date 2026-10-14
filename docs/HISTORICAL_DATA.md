# Provider history collected for research

On October 14, 2026 UTC, the operator requested a full-year historical backfill.
All four five-minute ingestion jobs completed for the half-open UTC interval
2025-10-14 00:00 through 2026-10-14 00:00. Candles are stored in the persistent
PostgreSQL volume under their original provider sources, separate from fixtures.

| Symbol | Source | Candles in requested interval | Gaps | Contiguous research windows* |
| --- | --- | ---: | ---: | ---: |
| EUR_USD | oanda | 74,589 | 57 | 70,599 |
| GBP_USD | oanda | 74,577 | 66 | 70,364 |
| BTC-USD | coinbase | 104,971 | 5 | 104,613 |
| ETH-USD | coinbase | 104,971 | 4 | 104,616 |

All series start at 2025-10-14 00:00 and end at 2026-10-13 23:55 UTC.
Total stored candles within this interval: 359,108. The audit found zero invalid
OHLC/volume/completeness/alignment rows and bid/ask components on every Forex row.
Database uniqueness prevents duplicate source/symbol/timeframe/timestamp rows.

\*Windows count contiguous 60-candle contexts plus 12 future label candles.
They are not counts of strategy candidates or trades. The trainer already
excludes candidate windows crossing gaps. Each crypto series has 149 absent
five-minute intervals out of 105,120 possible calendar intervals; targeted
re-requests returned no additional candles. Short Forex gaps were also
re-requested without recovering additional rows. Forex closure and holiday
classifications remain unverified pending an independent session calendar.
No gaps were filled with fabricated data.

The full gap list and per-series row hashes are saved in the research volume:
`data/reports/provider-history-2025-10-14-to-2026-10-14.json`. A local copy is
also in the ignored root `data/reports` directory. Provider candles, reports,
models and credentials are not committed to Git. Preserve the PostgreSQL and
research volumes to retain this evidence.

Main ingestion job IDs:

- EUR_USD: `6a49d99b-2a2e-4fbc-8e3c-1235185179db`
- GBP_USD: `20d9300d-e999-4266-9f7a-de4b37bd746b`
- BTC-USD: `d9416a1f-ee44-4189-8d72-6d1b50149aec`
- ETH-USD: `f41a1eb5-ceb5-4ace-a18e-a3c0a06e9f93`

## Display and training limits

The dashboard requests the latest 300 candles by default. The candle API allows
up to 1,000 per request. These display limits do not truncate the database.
`train-candidates` loads up to 1,000,000 matching provider candles independently
of the chart. The live worker maintains recent history; use the explicit
`download` command for older data.

Reproduce the requested backfill from the root folder with Docker running:

```powershell
foreach ($symbol in @('EUR_USD', 'GBP_USD', 'BTC-USD', 'ETH-USD')) {
    docker compose exec -T backend python -m app.cli download --symbol $symbol --timeframe 300 --start 2025-10-14T00:00:00+00:00 --end 2026-10-14T00:00:00+00:00
    if ($LASTEXITCODE -ne 0) { throw "Download failed for $symbol" }
}
```

Existing provider data outside this interval remains preserved, including the
older isolated BTC sample. Training currently loads all matching source history,
so define and inspect the intended dataset boundaries before the next experiment.
The one-year audit does not attest to data outside its requested interval.

## Next research step and verification

Collect and review instrument-specific spread, slippage, fee and financing
assumptions, then train provider-data candidates with chronological partitions.
Review calibration, net results, stressed costs and gaps using the predeclared
policy in MODEL_ACCEPTANCE.md. Data availability alone does not qualify a model.
Independent execution-quality/session validation remains outstanding. No model
was trained or activated by this download; the order count remained zero.

Verification after import: 117 backend tests passed including PostgreSQL cases,
9 frontend tests passed, TypeScript/Vite production build passed, Alembic found
no new upgrade operations, and dashboard/API/worker smoke checks passed. Existing
Starlette and sparse-class synthetic calibration warnings remain. Application
code and trading configuration were unchanged by this operation.
