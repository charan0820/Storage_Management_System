import pytest

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    from backend.database import db
    from backend.services import monitoring
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monitoring._recent_values.clear()
    monitoring._last_status.clear()
    monitoring._sources.clear()
