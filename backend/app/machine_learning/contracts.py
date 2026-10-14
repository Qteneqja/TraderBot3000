"""Bind artifacts to the feature, strategy, simulator and risk implementations they evaluated."""

from hashlib import sha256
from pathlib import Path

from app.machine_learning.policy import digest

FILES = (
    "indicators/features.py", "strategies/registry.py", "machine_learning/candidate_training.py",
    "machine_learning/registry.py", "backtesting/simulator.py", "backtesting/portfolio.py",
    "risk_management/engine.py", "execution/paper.py",
    "machine_learning/contracts.py",
    "market_data/coverage.py", "market_data/fingerprint.py",
    "backtesting/registered.py",
)


def research_code_contract():
    root = Path(__file__).resolve().parents[1]
    files = {name: sha256((root / name).read_text(encoding="utf-8").encode()).hexdigest() for name in FILES}
    contract = {"schema": "research-code-v1", "files": files}
    return contract | {"sha256": digest(contract)}
