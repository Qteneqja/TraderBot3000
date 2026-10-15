# Execution-cost validation

Evidence collected 2026-10-15 22:11 UTC using read-only OANDA practice endpoints. Source: ignored `/app/data/reports/execution-cost-evidence-20261015-v1.json`. Execution authority: **NONE**. Economic qualification: **BLOCKED_BY_UNVERIFIED_HISTORICAL_EXECUTION_COSTS**.

The practice account is OANDA Canada, CAD. The existing research/PAPER account is USD. They are separate ledgers; USD research returns cannot be relabeled as CAD practice P&L. Current broker gain, loss and position conversion factors were separately observed; the historical CAD conversion path remains UNKNOWN.

| Component | Classification | Actual evidence / limitation |
| --- | --- | --- |
| EUR/USD historic candle-close full spread | OBSERVED | 47,683 protected pre-final candles; median .00016, p95 .00020, p99 .00052, max .00100 |
| GBP/USD historic candle-close full spread | OBSERVED | 48,843 protected pre-final candles; median .00019, p95 .00029, p99 .00120, max .00200 |
| Account-specific commission / minimum charge | UNKNOWN | Instrument response did not disclose commission. Absence is not zero. |
| EUR/USD current signed annual financing | OBSERVED | Long -.0245; short +.0043; snapshot only, not a historical rate series |
| GBP/USD current signed annual financing | OBSERVED | Long -.0121; short -.0083; snapshot only |
| Financing days | OBSERVED | Broker instrument terms: Wednesday three days, weekdays one, weekends zero; holidays still need actual date-specific terms |
| Rollover mechanism | BROKER_DOCUMENTED | Canadian financing documentation; actual account/date applicability must still be checked |
| Historical financing and CAD conversions | UNKNOWN | No verified historical rate/conversion path has been obtained |
| Slippage / executable intrabar spread | ESTIMATED / UNKNOWN | Existing one adverse tick assumption; no confirmed practice fill evidence |
| Crypto maker/taker fee, account tier, historical spread | UNKNOWN | Existing research uses estimated .012 per side (1.2%); it is not an observed account fee |

Spread observations are bid/ask candle **close** components, not intrabar paths, order-book depth, execution prices or guaranteed fills. Historical spread statistics end before the common final decision boundary; no final-test outcomes were used. The forensic scanner additionally excludes the candle completing exactly at that boundary, hence its prefix counts are one smaller.

OANDA documents rollover at 5 p.m. New York time, variable instrument/direction rates and multi-day charges; public indicative rates do not establish an account's historical charges. See [OANDA Canada financing](https://www.oanda.com/ca-en/trading/financing-costs/) and [v20 instrument commission/financing schema](https://developer.oanda.com/rest-live-v20/primitives-df/). Current signed rates must not be converted into a perpetual constant zero or applied retroactively without evidence.

The new bounded comparisons freeze old estimated costs for comparability. They are not cost-qualified. Required next work: obtain the actual commission schedule/minimum fee and historical financing terms, model holiday rollover and CAD cashflows, validate rounding against account instrument precision, then preregister a new cost-bound comparison. Keep unknown inputs explicit. Actual slippage/protection/fees require the separately gated practice lifecycle acceptance; no order was sent for this report.

Recollect a new uniquely named snapshot without overwriting old evidence:

```powershell
docker compose exec backend python -m app.research.costs --output /app/data/reports/cost-evidence-NEW-UNIQUE.json
```

This performs read-only broker requests. It cannot qualify a model or enable submission.
