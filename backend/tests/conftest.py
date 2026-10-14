"""Keep user credentials and application databases out of the test process."""

import os

import pytest

from app.core.config import Settings, get_settings

# Collection imports the API and database modules. Isolate settings before those imports,
# not in a later fixture. Explicit TEST_POSTGRES_URL remains available to schema-isolated tests.
for name in Settings.model_fields:
    os.environ.pop(name.upper(), None)
Settings.model_config["env_file"] = None
get_settings.cache_clear()


@pytest.fixture
def execution_model_stub(monkeypatch):
    """Isolate ledger/fault tests from ML; deployment tests exercise the real gate separately."""
    from app.models.tables import ModelVersion

    def authorize(db, candidate, quote, settings, now):
        model = db.get(ModelVersion, candidate.model_version) if candidate.model_version else None
        allowed = model is not None and model.metadata_json.get("execution_validated") is True
        return candidate.model_copy(update={"calibrated": candidate.calibrated and allowed})

    monkeypatch.setattr("app.execution.paper.authorize_candidate", authorize)
