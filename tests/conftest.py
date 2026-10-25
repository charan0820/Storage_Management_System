import pytest
import os
from pathlib import Path
from tempfile import TemporaryDirectory


def pytest_configure(config):
    # backend.app creates its global Flask app during collection, before fixtures.
    # Isolate that bootstrap too, so schema migrations never touch the user's DB.
    config._storewatch_temp = TemporaryDirectory(prefix='storewatch-tests-')
    config._storewatch_original_db = os.environ.get('STOREWATCH_DB')
    os.environ['STOREWATCH_DB'] = str(Path(config._storewatch_temp.name) / 'bootstrap.db')


def pytest_unconfigure(config):
    original = getattr(config, '_storewatch_original_db', None)
    if original is None:
        os.environ.pop('STOREWATCH_DB', None)
    else:
        os.environ['STOREWATCH_DB'] = original
    temporary = getattr(config, '_storewatch_temp', None)
    if temporary:
        temporary.cleanup()

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    from backend.database import db
    from backend.services import monitoring
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monitoring._recent_values.clear()
    monitoring._last_status.clear()
    monitoring._sources.clear()
