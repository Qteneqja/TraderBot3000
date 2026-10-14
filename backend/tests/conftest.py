"""Keep user credentials and application databases out of the test process."""

import os

from app.core.config import Settings, get_settings

# Collection imports the API and database modules. Isolate settings before those imports,
# not in a later fixture. Explicit TEST_POSTGRES_URL remains available to schema-isolated tests.
for name in Settings.model_fields:
    os.environ.pop(name.upper(), None)
Settings.model_config["env_file"] = None
get_settings.cache_clear()
