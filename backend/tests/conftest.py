import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Prototype-owned tables go to a scratch file for the test run, so pytest never leaves
# test rows (RQs, highlights, voice memos...) behind in db/prototype.db, the real dev
# database. The Cortico snapshot stays the real, read-only one — tests should run against
# real data there, not a copy.
os.environ.setdefault("PROTOTYPE_DB_PATH", os.path.join(tempfile.mkdtemp(), "test_prototype.db"))

import pytest  # noqa: E402

from app import models_prototype  # noqa: E402, F401 — registers tables on PrototypeBase
from app.db import PrototypeBase, prototype_engine  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _create_prototype_tables():
    PrototypeBase.metadata.create_all(bind=prototype_engine)
