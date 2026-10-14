from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

D = Decimal


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class Candle(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    symbol: str
    timeframe: int = Field(gt=0)
    time: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(default=D(0), ge=0)
    complete: bool = True
    source: str
    provenance: dict = Field(default_factory=dict)

    @field_validator("time")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return aware(value)

    @model_validator(mode="after")
    def valid_range(self):
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid OHLC range")
        if int(self.time.timestamp()) % self.timeframe or self.time.microsecond:
            raise ValueError("Candle timestamp is not aligned to timeframe")
        return self


class Quote(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    symbol: str
    time: datetime
    bid: Decimal = Field(gt=0)
    ask: Decimal = Field(gt=0)
    source: str

    @field_validator("time")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError("Quote timestamp must include timezone")
        return aware(value)

    @model_validator(mode="after")
    def spread(self):
        if self.ask < self.bid:
            raise ValueError("Crossed quote")
        return self


class Candidate(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, frozen=True)
    id: str
    symbol: str
    strategy: str
    direction: Literal["LONG", "SHORT"]
    time: datetime
    expires_at: datetime
    entry: Decimal = Field(gt=0)
    stop: Decimal = Field(gt=0)
    target: Decimal = Field(gt=0)
    timeframe: int = Field(gt=0)
    regime: str
    features: dict[str, float]
    invalidation: str
    source: str
    model_version: str | None = None
    probability: Decimal | None = Field(default=None, ge=0, le=1)
    probability_stop: Decimal | None = Field(default=None, ge=0, le=1)
    probability_timeout: Decimal | None = Field(default=None, ge=0, le=1)
    timeout_return: Decimal = D(0)
    calibrated: bool = False
    shadow_prediction: dict | None = None

    @field_validator("time", "expires_at")
    @classmethod
    def utc(cls, value):
        if value.tzinfo is None:
            raise ValueError("Candidate timestamps must include a timezone")
        return aware(value)

    @model_validator(mode="after")
    def expiry_order(self):
        if self.expires_at <= self.time:
            raise ValueError("Candidate expiration must follow generation")
        return self


class RiskDecision(BaseModel):
    approved: bool
    reasons: list[str]
    units: Decimal = D(0)
    planned_risk: Decimal = D(0)
    expected_value: Decimal | None = None
    reward_risk: Decimal | None = None
