from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.indicators.features import compute, frame
from app.machine_learning.registry import ModelUnavailable, record_prediction, shadow_predict
from app.models.tables import ModelVersion
from app.schemas.domain import Quote
from app.strategies.registry import candidates_from_row


def replay_shadow(db, candles, version_id: str, artifact_root: Path, limit=200):
    """Historical shadow observations only. Never calls an execution adapter."""
    if not 1 <= limit <= 10000:
        raise ValueError("Replay limit must be between 1 and 10000 candles")
    version = db.get(ModelVersion, version_id)
    if not version or version.status != "SHADOW":
        raise ModelUnavailable("Explicitly deploy the chosen model to SHADOW before replay")
    metadata = version.metadata_json
    data = compute(frame(candles))
    tick = Decimal(metadata["tick"])
    spread = Decimal(metadata["costs"]["spread"])
    recorded = 0
    for i in range(max(59, len(candles) - limit), len(candles) - 1):
        candle = candles[i]
        when = candle.time + timedelta(seconds=candle.timeframe)
        if pd.Timestamp(when) < pd.Timestamp(metadata["training_cutoff"]):
            continue
        if (
            data.index[i - 59 : i + 2].to_series().diff().dropna().dt.total_seconds() != candle.timeframe
        ).any():
            continue
        candidates = candidates_from_row(
            data.iloc[i], candle.symbol, candle.timeframe, candle.source, when, tick, [metadata["strategy"]]
        )
        quote = Quote(
            symbol=candle.symbol,
            time=when,
            source=candle.source,
            bid=candles[i + 1].open - spread / 2,
            ask=candles[i + 1].open + spread / 2,
        )
        for candidate in candidates:
            market = quote.ask if candidate.direction == "LONG" else quote.bid
            if abs(market - candidate.entry) > max(
                abs(candidate.entry - candidate.stop) * Decimal("0.1"), tick * 2
            ):
                continue
            prediction = shadow_predict(db, candidate, quote, artifact_root)
            if prediction:
                prediction["quote_assumption"] = "Historical next open plus configured constant spread"
                record_prediction(db, candidate, quote, prediction, "SHADOW_REPLAY")
                recorded += 1
    return {"evaluated": recorded, "mode": "SHADOW_REPLAY", "execution_allowed": False}
