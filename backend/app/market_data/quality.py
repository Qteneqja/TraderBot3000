from datetime import datetime, timedelta

from app.schemas.domain import Candle


def inspect_candles(candles: list[Candle], now: datetime) -> dict:
    issues = []
    gaps = []
    seen = set()
    previous = None
    for c in candles:
        key = (c.symbol, c.timeframe, c.time, c.source)
        if key in seen:
            issues.append({"kind": "duplicate", "time": c.time.isoformat()})
        seen.add(key)
        end = c.time + timedelta(seconds=c.timeframe)
        if not c.complete or end > now:
            issues.append({"kind": "incomplete_or_future", "time": c.time.isoformat()})
        if previous:
            if (previous.symbol, previous.timeframe, previous.source) != (c.symbol, c.timeframe, c.source):
                issues.append({"kind": "mixed_series", "time": c.time.isoformat()})
            if c.time <= previous.time:
                issues.append({"kind": "out_of_order", "time": c.time.isoformat()})
            if (c.time - previous.time).total_seconds() > c.timeframe:
                # Closures need a verified provider calendar; never silently mark gaps as weekends.
                gaps.append(
                    {
                        "after": previous.time.isoformat(),
                        "before": c.time.isoformat(),
                        "classification": "unverified_closure_or_missing_data",
                    }
                )
        previous = c
    return {
        "count": len(candles),
        "issues": issues,
        "gaps": gaps,
        "execution_quality": False,
        "valid": not issues,
    }
