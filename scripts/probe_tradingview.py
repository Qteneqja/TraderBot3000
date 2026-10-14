"""Bounded, anonymous tvdatafeed diagnostic; never imports data into the bot.

Run with a separate Python environment containing tvdatafeed. Results describe
library output, not validated training data. Login is opt-in via --login.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CHILD = r'''
import json
import logging
import os
import sys

logging.disable(logging.CRITICAL)
try:
    from tvDatafeed import TvDatafeed, Interval
    symbol, exchange, interval, count, login = sys.argv[1:]
    tv = TvDatafeed(os.environ["TRADINGVIEW_USERNAME"], os.environ["TRADINGVIEW_PASSWORD"]) if login == "yes" else TvDatafeed()
    if login == "yes" and tv.token == "unauthorized_user_token":
        print(json.dumps({"status": "AUTHENTICATION_FAILED"}))
        sys.exit(0)
    try:
        frame = tv.get_hist(symbol=symbol, exchange=exchange,
                            interval=getattr(Interval, interval), n_bars=int(count))
    finally:
        if tv.ws is not None:
            tv.ws.close()
    if frame is None or frame.empty:
        result = {"status": "NO_DATA"}
    else:
        result = {
            "status": "RECEIVED_UNVALIDATED",
            "rows": len(frame),
            "first_timestamp": str(frame.index.min()),
            "last_timestamp": str(frame.index.max()),
            "timestamp_basis": "library host-local naive datetime; not normalized UTC",
            "calendar_span_days": (frame.index.max() - frame.index.min()).total_seconds() / 86400,
            "duplicates": int(frame.index.duplicated().sum()),
            "monotonic": bool(frame.index.is_monotonic_increasing),
            "missing_cells": int(frame.isna().sum().sum()),
            "columns": list(frame.columns),
        }
except Exception as exc:
    # Exception messages/third-party logs may include remote headers or tokens.
    result = {"status": "ERROR", "error_type": type(exc).__name__}
print(json.dumps(result))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", action="store_true", help="Read TradingView credentials from ignored .env")
    args = parser.parse_args()
    child_env = os.environ.copy()
    if args.login:
        from dotenv import dotenv_values

        values = dotenv_values(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
        for name in ("TRADINGVIEW_USERNAME", "TRADINGVIEW_PASSWORD"):
            value = values.get(name) or child_env.get(name)
            if not value:
                parser.error(f"Set {name} in the ignored local .env before using --login")
            child_env[name] = value
    cases = [
        ("NIFTY", "NSE", "in_1_hour", "1000"),
        ("EURUSD", "OANDA", "in_5_minute", "5000"),
        ("BTCUSD", "COINBASE", "in_5_minute", "5000"),
    ]
    for symbol, exchange, interval, bars in cases:
        result = {
            "symbol": symbol, "exchange": exchange, "interval": interval,
            "requested": int(bars), "authenticated_requested": args.login,
        }
        try:
            completed = subprocess.run(
                [sys.executable, "-c", CHILD, symbol, exchange, interval, bars, "yes" if args.login else "no"],
                env=child_env,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
            if completed.returncode:
                result.update(status="PROCESS_ERROR", returncode=completed.returncode)
            else:
                result.update(json.loads(completed.stdout))
        except subprocess.TimeoutExpired:
            result.update(status="TIMEOUT", timeout_seconds=45)
        except (ValueError, OSError) as exc:
            result.update(status="PROBE_ERROR", error_type=type(exc).__name__)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
