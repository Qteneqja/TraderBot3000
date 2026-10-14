"""Canonical input provenance, independent of database Decimal scale."""

import hashlib
import json
from datetime import datetime


def candle_manifest(candles):
    if not candles:
        raise ValueError("Cannot fingerprint an empty dataset")
    digest = hashlib.sha256()
    for candle in candles:
        row = candle.model_dump(mode="json")
        for name in ("open", "high", "low", "close", "volume"):
            row[name] = format(getattr(candle, name).normalize(), "f")
        digest.update(json.dumps(row, sort_keys=True, separators=(",", ":")).encode())
        digest.update(b"\n")
    return {
        "sha256": digest.hexdigest(),
        "count": len(candles),
        "start": candles[0].time.isoformat(),
        "end": candles[-1].time.isoformat(),
    }


def verified_training_rows(candles, manifest):
    if not manifest:
        raise ValueError("Model lacks an input candle manifest; retrain before reproducible evaluation")
    start, end = (datetime.fromisoformat(manifest[k]) for k in ("start", "end"))
    rows = [c for c in candles if start <= c.time <= end]
    if not rows or candle_manifest(rows) != manifest:
        raise ValueError("Model input candles changed or are missing; evaluation blocked")
    return rows
