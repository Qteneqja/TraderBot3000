"""Explicit, account-scoped PAPER trials. Research artifacts remain immutable."""

from datetime import datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

from sqlalchemy import select

from app.machine_learning.policy import acceptance_policy, digest, risk_contract
from app.machine_learning.registry import ModelUnavailable, load_verified, predict_version
from app.market_data.fingerprint import verified_training_rows
from app.market_data.store import load_candles
from app.models.tables import (
    Event,
    Instrument,
    ModelPrediction,
    ModelReview,
    ModelVersion,
    PaperDeployment,
    PaperDeploymentSlot,
)
from app.schemas.domain import aware
from app.strategies.registry import evaluate

SCOPE_KEYS = ("symbol", "strategy", "timeframe", "source")
PREREQUISITES = {
    "PAPER_RESEARCH_MODE",
    "ARTIFACT_INTEGRITY",
    "POLICY_PREDECLARED_AND_UNCHANGED",
    "REAL_MARKET_SOURCE",
    "HISTORY_DURATION",
    "CALIBRATION_SAMPLE_COUNT",
    "THRESHOLD_AND_REWARD_FLOOR",
}
PARTITION_CHECKS = {
    "PARTITION_DURATION",
    "TRADE_COUNT",
    "ACTIVE_DAYS",
    "POSITIVE_NET_RETURN",
    "POSITIVE_EXPECTANCY",
    "PROFIT_FACTOR",
    "DRAWDOWN",
    "CALIBRATION",
    "BEATS_CLASS_BASELINE",
    "UNCERTAINTY_LOWER_BOUND",
    "STRESSED_ACTIVITY",
    "STRESSED_NET_RETURN",
    "STRESSED_DRAWDOWN",
}


def scope_key(metadata):
    return digest({key: metadata[key] for key in SCOPE_KEYS})


def runtime_contract(settings):
    return {
        "risk": risk_contract(settings),
        "mode": settings.trading_mode,
        "demo": settings.demo_mode,
        "fee_rate": str(settings.paper_fee_rate),
        "slippage_ticks": settings.paper_slippage_ticks,
        "financing_per_bar": str(settings.paper_financing_per_unit_per_bar),
        "max_quote_age_seconds": settings.max_quote_age_seconds,
    }


def validate_evidence(db, version_id, review_id, root, settings):
    if settings.trading_mode != "PAPER" or settings.demo_mode:
        raise ModelUnavailable("Paper trials require PAPER mode and real market data")
    version, review = db.get(ModelVersion, version_id), db.get(ModelReview, review_id)
    if version is None or review is None or review.model_id != version_id:
        raise ModelUnavailable("Model and review must exist and refer to the same version")
    if version.status not in ("EXPERIMENTAL", "SHADOW", "RETIRED"):
        raise ModelUnavailable("Unsupported research model state")
    metadata, report = version.metadata_json, review.report
    if (
        digest(report) != review.id
        or review.status != "RESEARCH_GATES_PASSED"
        or report.get("status") != review.status
        or report.get("schema") != "model-assessment-v1"
        or report.get("model_version") != version.id
        or report.get("artifact_sha256") != metadata.get("artifact_sha256")
        or report.get("dataset_sha256") != metadata.get("dataset_sha256")
        or report.get("policy") != acceptance_policy(settings)
        or metadata.get("acceptance_policy") != report.get("policy")
        or not PREREQUISITES.issubset(report.get("checks", {}))
        or not all(value is True for value in report["checks"].values())
        or set(report.get("partitions", {})) != {"validation", "test"}
        or report.get("reasons") != []
        or report.get("execution_allowed") is not False
        or metadata.get("source") not in ("oanda", "coinbase")
    ):
        raise ModelUnavailable("Research review is rejected, changed or incompatible")
    for name, part in report["partitions"].items():
        if not PARTITION_CHECKS.issubset(part.get("checks", {})) or not all(
            v is True for v in part["checks"].values()
        ):
            raise ModelUnavailable("Incomplete held-out partition checks")
        if not all(report["checks"].get(f"{name.upper()}_{key}") is True for key in PARTITION_CHECKS):
            raise ModelUnavailable("Partition checks differ from review summary")
        if not part.get("replay_sha256") or not part.get("stress_replay_sha256"):
            raise ModelUnavailable("Missing held-out replay evidence")
    instrument = db.get(Instrument, metadata["symbol"])
    costs = metadata["costs"]
    if (
        instrument is None
        or instrument.provider != metadata["source"]
        or metadata["horizon"] != 12
        or metadata["timeframe"] != 300
        or D(metadata["tick"]) != instrument.tick_size
        or D(costs["slippage"]) != instrument.tick_size * settings.paper_slippage_ticks
        or D(costs["fee_rate"]) != settings.paper_fee_rate
        or D(costs["financing_per_bar"]) != settings.paper_financing_per_unit_per_bar
        or not D(costs["spread"]).is_finite()
        or D(costs["spread"]) <= 0
    ):
        raise ModelUnavailable("Runtime scope or costs differ from reviewed research")
    model = load_verified(version, root)
    contract = {
        "schema": "paper-trial-v1",
        "scope": {key: metadata[key] for key in SCOPE_KEYS},
        "artifact_sha256": metadata["artifact_sha256"],
        "metadata_sha256": digest(metadata),
        "review_id": review.id,
        "runtime": runtime_contract(settings),
        "instrument": {
            key: str(getattr(instrument, key))
            for key in ("tick_size", "unit_step", "min_units", "max_spread")
        },
        "purpose": "Supervised paper trial; no broker execution approval",
    }
    return version, model, contract


def activate(db, version_id, review_id, root, settings, operator, reason, now, rollback_to=None):
    from app.execution.paper import lock_account

    if not operator.strip() or len(operator) > 120 or not reason.strip() or len(reason) > 512:
        raise ValueError("Operator and reason are required (maximum 120 and 512 characters)")
    try:
        account = lock_account(db)
        if account.suspended or not account.reconciled:
            raise ModelUnavailable("Account must be reconciled and unsuspended")
        version, _, contract = validate_evidence(db, version_id, review_id, root, settings)
        rows = load_candles(
            db, version.metadata_json["symbol"], 300, version.metadata_json["source"], 1_000_000
        )
        verified_training_rows(rows, version.metadata_json["input_candles"])
        history_end = aware(datetime.fromisoformat(version.metadata_json["input_candles"]["end"]))
        if history_end + timedelta(seconds=300) > now:
            raise ModelUnavailable("Research outcomes must precede activation")
        key = scope_key(version.metadata_json)
        slot = db.get(PaperDeploymentSlot, (account.id, key))
        if rollback_to:
            prior = db.get(PaperDeployment, rollback_to)
            if (
                prior is None
                or prior.account_id != account.id
                or prior.scope_key != key
                or prior.model_id != version_id
                or prior.review_id != review_id
            ):
                raise ModelUnavailable("Rollback target does not match this account and scope")
        if slot and slot.deployment_id:
            current = db.get(PaperDeployment, slot.deployment_id)
            if (
                current.model_id == version_id
                and current.contract == contract
                and (rollback_to is None or current.rollback_of == rollback_to)
            ):
                result = current.id
                db.rollback()
                return result
        deployment = PaperDeployment(
            account_id=account.id,
            scope_key=key,
            model_id=version.id,
            review_id=review_id,
            previous_id=slot.deployment_id if slot else None,
            rollback_of=rollback_to,
            operator=operator.strip(),
            reason=reason.strip(),
            contract=contract,
            created_at=now,
        )
        db.add(deployment)
        db.flush()
        if slot is None:
            slot = PaperDeploymentSlot(account_id=account.id, scope_key=key)
            db.add(slot)
        slot.deployment_id = deployment.id
        db.add(
            Event(
                kind="paper_model_rollback" if rollback_to else "paper_model_activated",
                detail={
                    "deployment": deployment.id,
                    "model": version.id,
                    "review": review_id,
                    "previous": deployment.previous_id,
                    "rollback_to": rollback_to,
                    "operator": operator.strip(),
                    "reason": reason.strip(),
                    "broker_execution_allowed": False,
                },
            )
        )
        result = deployment.id
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def rollback(db, deployment_id, root, settings, operator, reason, now):
    target = db.get(PaperDeployment, deployment_id)
    if target is None:
        db.rollback()
        raise ModelUnavailable("Unknown rollback target")
    version, review = target.model_id, target.review_id
    db.rollback()
    return activate(db, version, review, root, settings, operator, reason, now, rollback_to=deployment_id)


def deactivate(db, deployment_id, operator, reason):
    from app.execution.paper import lock_account

    if not operator.strip() or len(operator) > 120 or not reason.strip() or len(reason) > 512:
        raise ValueError("Operator and reason are required (maximum 120 and 512 characters)")
    try:
        lock_account(db)
        deployment = db.get(PaperDeployment, deployment_id)
        if deployment is None:
            raise ModelUnavailable("Unknown deployment")
        slot = db.get(PaperDeploymentSlot, ("PAPER", deployment.scope_key))
        if slot and slot.deployment_id == deployment_id:
            slot.deployment_id = None
            db.add(
                Event(
                    kind="paper_model_deactivated",
                    detail={
                        "deployment": deployment_id,
                        "operator": operator.strip(),
                        "reason": reason.strip(),
                    },
                )
            )
        else:
            raise ModelUnavailable("Deployment is no longer current; refresh before deactivating")
        db.commit()
    except Exception:
        db.rollback()
        raise


def authorize_candidate(db, candidate, quote, settings, now):
    """Called under the account lock. Ignore caller probabilities and reconstruct the proposal."""
    denied = candidate.model_copy(
        update={
            "calibrated": False,
            "model_version": None,
            "deployment_id": None,
            "probability": None,
            "probability_stop": None,
            "probability_timeout": None,
        }
    )
    slot = db.get(PaperDeploymentSlot, ("PAPER", scope_key(candidate.model_dump())))
    if slot is None or slot.deployment_id is None:
        return denied
    deployment = db.get(PaperDeployment, slot.deployment_id)
    try:
        version, model, contract = validate_evidence(
            db, deployment.model_id, deployment.review_id, Path(settings.model_artifact_dir), settings
        )
        if contract != deployment.contract or candidate.time < aware(deployment.created_at):
            raise ModelUnavailable("Deployment contract changed or candidate predates activation")
        if not candidate.time <= now < candidate.expires_at:
            raise ModelUnavailable("Candidate is outside its validity interval")
        if quote.ask - quote.bid > D(version.metadata_json["costs"]["spread"]):
            raise ModelUnavailable("Current spread exceeds reviewed cost assumption")
        instrument = db.get(Instrument, candidate.symbol)
        rows = load_candles(db, candidate.symbol, candidate.timeframe, candidate.source)
        proposals = evaluate(rows, candidate.time, instrument.tick_size, [candidate.strategy])
        canonical = next((p for p in proposals if p.id == candidate.id), None)
        if canonical is None or canonical.time != candidate.time:
            raise ModelUnavailable("Candidate cannot be reproduced from stored completed candles")
        prediction = predict_version(version, canonical, quote, model)
        authorized = canonical.model_copy(
            update={
                "calibrated": True,
                "model_version": version.id,
                "deployment_id": deployment.id,
                "probability": D(str(prediction["probability_target"])),
                "probability_stop": D(str(prediction["probability_stop"])),
                "probability_timeout": D(str(prediction["probability_timeout"])),
                "shadow_prediction": candidate.shadow_prediction,
            }
        )
        # Same model may also run in shadow: keep the existing observation and persist the
        # authoritative trial prediction in the signal payload atomically with the risk decision.
        existing = db.scalar(
            select(ModelPrediction).where(
                ModelPrediction.model_id == version.id, ModelPrediction.candidate_id == candidate.id
            )
        )
        if existing is None:
            db.add(
                ModelPrediction(
                    model_id=version.id,
                    candidate_id=candidate.id,
                    symbol=candidate.symbol,
                    time=candidate.time,
                    quote_time=quote.time,
                    mode="PAPER_TRIAL",
                    prediction=prediction | {"deployment_id": deployment.id, "execution_allowed": False},
                    candidate=authorized.model_dump(mode="json"),
                )
            )
        return authorized
    except (ModelUnavailable, ValueError, KeyError, TypeError, ArithmeticError):
        db.add(
            Event(
                kind="paper_model_blocked",
                detail={"deployment": deployment.id, "reason": "EVIDENCE_OR_INFERENCE_INVALID"},
            )
        )
        return denied
