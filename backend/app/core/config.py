from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "AegisTrade AI"
    app_env: str = "development"
    database_url: str = "sqlite:///./aegis.db"
    trading_mode: Literal["SIGNAL_ONLY", "PAPER", "OANDA_PRACTICE", "LIVE"] = "PAPER"
    enable_live_trading: bool = False
    demo_mode: bool = True
    model_artifact_dir: str = "model_artifacts"
    paper_fee_rate: Decimal = Field(default=Decimal(0), ge=0, lt=1)
    paper_slippage_ticks: int = Field(default=1, ge=0, le=100)
    paper_financing_per_unit_per_bar: Decimal = Field(default=Decimal(0), ge=0)
    admin_token: SecretStr = SecretStr("")
    oanda_api_key: SecretStr = SecretStr("")
    oanda_account_id: str = ""
    oanda_environment: Literal["practice"] = "practice"
    oanda_division: Literal["UNVERIFIED", "CA"] = "UNVERIFIED"
    llm_provider: Literal["deepseek", "openai"] = "deepseek"
    llm_model: str = "deepseek-flash"
    deepseek_api_key: SecretStr = SecretStr("")
    enable_llm_narratives: bool = False
    llm_max_calls_per_day: int = Field(default=4, ge=1, le=24)
    llm_min_interval_seconds: int = Field(default=60, ge=1, le=86400)
    openai_api_key: SecretStr = SecretStr("")
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""
    enable_notifications: bool = False
    enable_drift_suspension: bool = False
    risk_per_trade: Decimal = Field(default=Decimal("0.005"), gt=0, le=Decimal("0.005"))
    max_daily_loss: Decimal = Field(default=Decimal("0.02"), gt=0, le=Decimal("0.02"))
    max_weekly_loss: Decimal = Field(default=Decimal("0.05"), gt=0, le=Decimal("0.05"))
    max_open_positions: int = Field(default=3, ge=1, le=3)
    initial_probability_threshold: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)
    min_risk_reward: Decimal = Field(default=Decimal("2"), ge=1)
    max_quote_age_seconds: int = Field(default=30, ge=1, le=120)
    max_drawdown: Decimal = Field(default=Decimal("0.10"), gt=0, le=Decimal("0.10"))
    max_portfolio_risk: Decimal = Field(default=Decimal("0.015"), gt=0, le=Decimal("0.015"))
    max_leverage: Decimal = Field(default=Decimal("3"), gt=0, le=Decimal("3"))

    @model_validator(mode="after")
    def disallow_live(self):
        if self.enable_live_trading or self.trading_mode == "LIVE":
            raise ValueError("LIVE execution is unsupported; use PAPER or OANDA_PRACTICE")
        if self.demo_mode and self.trading_mode == "OANDA_PRACTICE":
            raise ValueError("Fixture data must never be sent to a broker; disable DEMO_MODE")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
