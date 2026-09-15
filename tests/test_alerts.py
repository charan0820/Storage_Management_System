import importlib

import pytest


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    import backend.database.db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    db_module.init_db()

    import backend.services.alert_service as alert_module
    importlib.reload(alert_module)
    return alert_module


def test_generate_alert_on_low_stock(fresh_db):
    alerts = fresh_db
    alert = alerts.generate_alert("SHELF_01", "LOW_STOCK")
    assert alert is not None
    assert alert["alert_type"] == "LOW_STOCK"
    assert alert["resolved"] == 0


def test_no_duplicate_alert_while_still_low(fresh_db):
    alerts = fresh_db
    first = alerts.generate_alert("SHELF_01", "LOW_STOCK")
    second = alerts.generate_alert("SHELF_01", "LOW_STOCK")
    assert first is not None
    assert second is None  # deduplicated, per Section 18


def test_alert_resolves_on_recovery(fresh_db):
    alerts = fresh_db
    alerts.generate_alert("SHELF_01", "EMPTY")
    result = alerts.generate_alert("SHELF_01", "FULL")
    assert result is None  # resolving doesn't create a new alert
    active = alerts.get_active_alerts()
    assert all(a["shelf_id"] != "SHELF_01" for a in active)


def test_new_alert_after_recovery_and_relapse(fresh_db):
    alerts = fresh_db
    alerts.generate_alert("SHELF_01", "LOW_STOCK")
    alerts.generate_alert("SHELF_01", "FULL")  # resolves
    relapse = alerts.generate_alert("SHELF_01", "LOW_STOCK")
    assert relapse is not None  # new alert allowed after resolution
