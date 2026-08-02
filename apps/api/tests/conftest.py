"""Force the test suite onto a local SQLite database.

Test modules import the application engine (`app.db.session.engine`) and call
`Base.metadata.drop_all()`. Without this file, anyone whose .env points
DATABASE_URL at a real database — Neon, staging, production — drops those
tables just by running pytest. Environment variables outrank the .env file in
pydantic-settings, and pytest imports conftest before any test module, so
setting it here wins regardless of local configuration.
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
