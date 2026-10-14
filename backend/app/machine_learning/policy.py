"""Predeclared research screening policy. Passing never grants execution authority."""

import hashlib
import json

from app.core.config import Settings

RISK_KEYS = (
    "risk_per_trade",
    "max_daily_loss",
    "max_weekly_loss",
    "max_open_positions",
    "max_portfolio_risk",
    "max_leverage",
    "max_drawdown",
    "initial_probability_threshold",
    "min_risk_reward",
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def risk_contract(settings):
    return {key: str(getattr(settings, key)) for key in RISK_KEYS}


def acceptance_policy(settings=None):
    settings = settings or Settings(_env_file=None)
    policy = {
        "version": "research-screen-v1",
        "purpose": "Eligibility for further paper deployment review; no execution permission",
        "minimum_history_days": 180,
        "minimum_partition_days": 30,
        "minimum_calibration_samples": 200,
        "minimum_partition_trades": 100,
        "minimum_active_days": 20,
        "minimum_profit_factor": 1.2,
        "maximum_drawdown": 0.08,
        "maximum_target_calibration_error": 0.05,
        "cost_stress_multiplier": 2,
        "bootstrap_block_days": 5,
        "bootstrap_draws": 2000,
        "bootstrap_seed": 42,
        "bootstrap_lower_quantile": 0.025,
        "risk_contract": risk_contract(settings),
    }
    return policy | {"sha256": digest(policy)}
