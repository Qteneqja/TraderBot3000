"""Read-only practice acceptance evidence; no result authorizes submission."""

from datetime import datetime, timezone
from decimal import Decimal as D
from hashlib import sha256


def decimal(value):
    result = D(str(value))
    if not result.is_finite():
        raise ValueError("Nonfinite broker value")
    return result


def instrument_contract(raw):
    precision, unit_precision = int(raw["displayPrecision"]), int(raw["tradeUnitsPrecision"])
    if not 0 <= precision <= 10 or not 0 <= unit_precision <= 10 or raw["type"] != "CURRENCY":
        raise ValueError("Unsupported broker instrument precision or type")
    minimum, maximum, margin = (decimal(raw[k]) for k in ("minimumTradeSize", "maximumOrderUnits", "marginRate"))
    if minimum <= 0 or maximum < minimum or not 0 < margin <= 1:
        raise ValueError("Invalid broker size or margin contract")
    return {"symbol": raw["name"], "tick": str(D(10) ** -precision),
            "unit_step": str(D(10) ** -unit_precision), "minimum_units": str(minimum),
            "maximum_order_units": str(maximum), "margin_rate": str(margin),
            "price_precision": precision, "unit_precision": unit_precision}


def conversion_contract(pricing, quote_currency, home_currency):
    if quote_currency == home_currency:
        return {"gain": D(1), "loss": D(1), "position": D(1)}
    matching = [c for c in pricing.get("homeConversions", []) if c.get("currency") == quote_currency]
    if len(matching) != 1:
        raise ValueError("Missing or ambiguous broker home conversion")
    result = {name: decimal(matching[0][key]) for name, key in (
        ("gain", "accountGain"), ("loss", "accountLoss"), ("position", "positionValue"))}
    if min(result.values()) <= 0:
        raise ValueError("Invalid broker conversion factors")
    return result


def validate_protection(trade, expected_symbol, signed_units, stop, target):
    units = decimal(trade["currentUnits"])
    entry = decimal(trade["price"])
    if trade["instrument"] != expected_symbol or units != signed_units or units == 0:
        raise ValueError("Broker exposure differs from reserved order")
    if not ((stop < entry < target) if units > 0 else (target < entry < stop)):
        raise ValueError("Invalid protection direction around confirmed fill")
    for name, price in (("stopLossOrder", stop), ("takeProfitOrder", target)):
        order = trade.get(name, {})
        if not order.get("id") or order.get("state") != "PENDING" or decimal(order.get("price")) != price:
            raise ValueError("Broker protection missing or mismatched")
        if str(order.get("tradeID")) != str(trade["id"]):
            raise ValueError("Protective order belongs to another trade")
    return True


async def readiness_report(adapter, account_id, symbols, now=None):
    if not symbols or not set(symbols) <= {"EUR_USD", "GBP_USD"} or len(set(symbols)) != len(symbols):
        raise ValueError("Practice readiness initially supports unique EUR_USD and GBP_USD scopes")
    properties = await adapter.account_properties()
    matching = [a for a in properties["accounts"] if a["id"] == account_id]
    if len(matching) != 1:
        raise ValueError("Configured practice account not uniquely accessible")
    response = await adapter.account_details()
    account = response["account"]
    if account["id"] != account_id:
        raise ValueError("Broker account identity mismatch")
    last = str(response.get("lastTransactionID", account.get("lastTransactionID", "")))
    if not last.isdigit():
        raise ValueError("Missing broker transaction watermark")
    instruments = await adapter.instruments()
    available = {i["name"]: i for i in instruments["instruments"]}
    contracts = [instrument_contract(available[s]) for s in symbols if s in available]
    pricing = await adapter.pricing(symbols)
    now = now or datetime.now(timezone.utc)
    prices = {p["instrument"]: p for p in pricing["prices"]}
    fresh, tradeable = True, True
    for symbol in symbols:
        price = prices.get(symbol)
        if not price:
            fresh, tradeable = False, False
            continue
        when = datetime.fromisoformat(price["time"].replace("Z", "+00:00"))
        bid, ask = decimal(price["bids"][0]["price"]), decimal(price["asks"][0]["price"])
        fresh = fresh and -2 <= (now - when).total_seconds() <= 30 and 0 < bid <= ask
        tradeable = tradeable and price.get("status") == "tradeable"
    transactions = await adapter.transactions(last)
    conversion = conversion_contract(pricing, "USD", account["currency"])
    positions_flat = all(decimal(p[side]["units"]) == 0 for p in account.get("positions", []) for side in ("long", "short"))
    checks = {
        "accessible_practice_account": True, "non_mt4_account": "mt4AccountID" not in matching[0],
        "quote_currency_conversion": min(conversion.values()) > 0,
        "positive_nav": decimal(account["NAV"]) > 0,
        "positive_free_margin": decimal(account["marginAvailable"]) > 0,
        "supported_guaranteed_stop_mode": account.get("guaranteedStopLossOrderMode", "DISABLED") != "REQUIRED",
        "all_instrument_contracts": len(contracts) == len(symbols),
        "fresh_quotes": fresh, "all_markets_tradeable": tradeable,
        "flat_account": not account.get("trades") and not account.get("orders") and positions_flat,
        "transaction_endpoint": str(transactions.get("lastTransactionID", "")).isdigit(),
        "stable_snapshot_watermark": str(transactions.get("lastTransactionID", "")) == last,
    }
    return {
        "schema": "oanda-practice-readiness-v1", "environment": "practice",
        "account_fingerprint": sha256(account_id.encode()).hexdigest(),
        "checked_at": now.isoformat(), "currency": account.get("currency"),
        "checks": checks, "instruments": contracts, "last_transaction_id": last,
        "usd_to_home_conversion": {k: str(v) for k, v in conversion.items()},
        "status": "READ_ONLY_CHECKS_PASSED" if all(checks.values()) else "BLOCKED",
        "submission_enabled": False,
        "remaining_gates": ["Durable reservations and complete transaction reconciliation",
                            "Verified model and sustained paper-trial approval",
                            "Explicit operator authorization for practice order testing",
                            "Confirmed fill/protection/closure and restart lifecycle verification"],
        "limitations": ["Conversion factors require a fresh broker pricing snapshot for every risk decision.",
                        "Read-only checks do not establish order execution readiness."],
    }
