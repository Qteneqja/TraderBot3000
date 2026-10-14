"""Reproducible research coverage, independent of prices or execution authority."""

from collections import Counter
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.market_data.fingerprint import candle_manifest
from app.market_data.quality import inspect_candles

CALENDAR_SOURCE = "https://www.oanda.com/us-en/trading/hours-of-operation/"
CA_SOURCE = "https://www.oanda.com/ca-en/trading/hours-of-operation/"
CA_HOLIDAYS = "https://www.oanda.com/ca-en/trading/holiday-trading-hours/"


def weekly_closed(when):
    """Approximate documented NY weekly closure only; holidays are never guessed."""
    local = when.astimezone(ZoneInfo("America/New_York"))
    return local.weekday() == 5 or (local.weekday() == 4 and local.hour >= 17) or (
        local.weekday() == 6 and local.hour < 17
    )


def canada_closed(when):
    """EUR/USD and GBP/USD only; dated overrides verified on 2026-10-14."""
    local = when.astimezone(ZoneInfo("America/New_York"))
    minute = local.hour * 60 + local.minute
    if local.weekday() == 5 or (local.weekday() == 4 and minute >= 1019):
        return True
    if local.weekday() == 6 and minute < 1025:
        return True
    # Official dated notices: close Dec 24/31 16:59, reopen Dec 25/Jan 1 17:05 NY.
    day = local.date().isoformat()
    if day in ("2025-12-24", "2025-12-31") and minute >= 1019:
        return True
    if day in ("2025-12-25", "2026-01-01") and minute < 1025:
        return True
    return 1019 <= minute < 1025


def session_closed(when, timeframe, division):
    if division == "CA":
        # An aligned candle is expected if ANY minute of its interval is tradable.
        return all(canada_closed(when + timedelta(seconds=offset)) for offset in range(0, timeframe, 60))
    return weekly_closed(when)


def coverage_report(candles, start, end, now, minimum_days=180, minimum_session_coverage=0.99,
                    oanda_division="UNVERIFIED"):
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("Coverage boundaries must be aware and increasing")
    if now.tzinfo is None or end > now:
        raise ValueError("Coverage cannot include future intervals")
    if not candles:
        return {"schema": "history-coverage-v1", "status": "EMPTY", "research_ready": False}
    symbol, source, timeframe = candles[0].symbol, candles[0].source, candles[0].timeframe
    if oanda_division not in ("UNVERIFIED", "CA"):
        raise ValueError("Unsupported OANDA calendar division")
    if source == "oanda" and oanda_division == "CA" and symbol not in ("EUR_USD", "GBP_USD"):
        raise ValueError("Canadian calendar currently verified only for EUR_USD and GBP_USD")
    if timeframe not in (60, 300, 900, 3600):
        raise ValueError("Unsupported coverage timeframe")
    if any(c.time < start or c.time + timedelta(seconds=timeframe) > end for c in candles):
        raise ValueError("Candles outside completed dataset interval")
    quality = inspect_candles(candles, now)
    times = {c.time for c in candles}
    cursor, absent, closed, expected = start, [], 0, 0
    if cursor.timestamp() % timeframe or end.timestamp() % timeframe:
        raise ValueError("Coverage boundaries must align to timeframe")
    while cursor < end:
        # Regional and holiday variations are disclosed; this never changes a price.
        if source == "oanda" and session_closed(cursor, timeframe, oanda_division):
            closed += 1
        else:
            expected += 1
            if cursor not in times:
                absent.append(cursor.isoformat())
        cursor += timedelta(seconds=timeframe)
    lengths, length, previous = [], 0, None
    usable_days = set()
    for candle in candles:
        if previous is not None and candle.time - previous != timedelta(seconds=timeframe):
            lengths.append(length)
            length = 0
        length += 1
        # A completed 60-bar context and 12-bar outcome must exist before counting a day.
        if length >= 72:
            usable_days.add((candle.time - timedelta(seconds=12 * timeframe)).date())
        previous = candle.time
    lengths.append(length)
    spreads = []
    for candle in candles:
        bid, ask = candle.provenance.get("bid"), candle.provenance.get("ask")
        if bid and ask:
            spread = Decimal(ask["c"]) - Decimal(bid["c"])
            if spread < 0:
                raise ValueError("Crossed historical bid/ask")
            spreads.append(spread)
    spreads.sort()
    checks = {
        "real_provider": source in ("oanda", "coinbase"),
        "valid_candles": quality["valid"],
        "minimum_calendar_span": (end - start).total_seconds() >= minimum_days * 86400,
        "minimum_usable_days": len(usable_days) >= minimum_days,
        "session_completeness": expected > 0 and (expected - len(absent)) / expected >= minimum_session_coverage,
    }
    return {
        "schema": "history-coverage-v2", "symbol": symbol, "source": source, "timeframe": timeframe,
        "requested_start": start.isoformat(), "requested_end_exclusive": end.isoformat(),
        "calendar_days": (end - start).total_seconds() / 86400,
        "input_candles": candle_manifest(candles), "quality": quality,
        "expected_weekly_session_candles": expected, "weekly_closed_intervals": closed,
        "calendar": ("oanda-ca-fx-v1" if oanda_division == "CA" else "approximate-oanda-ny-week-v1") if source == "oanda" else "24h-calendar",
        "calendar_source": (CA_SOURCE if oanda_division == "CA" else CALENDAR_SOURCE) if source == "oanda" else None,
        "holiday_source": CA_HOLIDAYS if source == "oanda" and oanda_division == "CA" else None,
        "calendar_verified_at": "2026-10-14" if source == "oanda" and oanda_division == "CA" else None,
        "unexplained_missing_count": len(absent), "unexplained_missing_timestamps": absent,
        "duplicate_candles": sum(n - 1 for n in Counter(c.time for c in candles).values()),
        "session_coverage": (expected - len(absent)) / expected if expected else 0,
        "minimum_session_coverage": minimum_session_coverage,
        "usable_days": len(usable_days),
        "contiguous_windows_60_context_12_outcome": sum(max(0, n - 71) for n in lengths),
        "spread": {"observations": len(spreads), "close_p99": str(spreads[int((len(spreads)-1)*.99)]) if spreads else None,
                   "maximum": str(spreads[-1]) if spreads else None},
        "checks": checks, "research_ready": all(checks.values()),
        "status": "RESEARCH_ONLY" if all(checks.values()) else "INSUFFICIENT",
        "model_qualification": "NOT_ASSESSED", "execution_quality": False,
        "limitations": ["Canada calendar covers regular EUR/GBP hours and dated Christmas 2025/New Year 2026 overrides only; other historical holiday variations remain unexplained."
                        if source == "oanda" and oanda_division == "CA" else "OANDA weekly calendar is approximate; division, daily breaks and holidays are unverified.",
                        "Missing intervals are preserved and training windows crossing them are excluded.",
                        "Close spreads do not attest to intrabar spreads, slippage, fees or financing."],
    }
