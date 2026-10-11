from datetime import datetime, timedelta, timezone
import pytest
from backend.app import app

def send(client, shelf="SHELF_01", cm=5, **extra):
    return client.post("/api/readings", json=dict(device_id="ESP32_01", shelf_id=shelf,
                       sensor_type="ultrasonic", distance_cm=cm, **extra))

def calibrate(client, shelf="SHELF_01", full=5, empty=30):
    return client.put("/api/shelves/"+shelf, json=dict(full_cm=full, empty_cm=empty, low_percent=25))

def test_waiting_uncalibrated_then_live():
    c=app.test_client()
    assert len(c.get("/api/shelves").json)==3
    assert all(s["status"]=="WAITING" for s in c.get("/api/shelves").json)
    assert send(c).json["status"]=="UNCALIBRATED"
    assert calibrate(c).status_code==200
    assert send(c).json["status"]=="FULL"
    s=c.get("/api/shelves").json[0]
    assert s["fill_percent"]==100 and s["product"]=="Coca-Cola" and s["online"]

def test_shelves_have_independent_calibration():
    c=app.test_client()
    calibrate(c)
    calibrate(c,"SHELF_02",10,50)
    assert send(c,cm=26).json["status"]=="LOW_STOCK"
    assert send(c,"SHELF_02",26).json["status"]=="NORMAL"

def test_fault_never_resolves_restock_and_does_not_pollute_filter():
    c=app.test_client();calibrate(c)
    assert send(c,cm=30).json["status"]=="EMPTY"
    assert send(c,cm=-1).json["status"]=="UNKNOWN"
    assert c.get("/api/alerts").json[0]["alert_type"]=="EMPTY"
    assert c.get("/api/shelves").json[0]["fill_percent"] is None
    assert send(c,cm=5).json["status"]=="FULL"
    assert c.get("/api/alerts").json==[]

def test_offline_overrides_old_stock():
    c=app.test_client();calibrate(c)
    stale=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat()
    send(c,cm=30,timestamp=stale)
    # Remove calibration invalidation for the old sample to model a running shelf.
    from backend.database.db import get_connection
    with get_connection() as conn:
        conn.execute("UPDATE shelves SET updated_at='' WHERE shelf_id='SHELF_01'")
    s=c.get("/api/shelves").json[0]
    assert s["status"]=="OFFLINE" and s["fill_percent"] is None

@pytest.mark.parametrize("value",[float('nan'),float('inf'),0,401,-2,'bad'])
def test_bad_sensor_values(value):
    assert send(app.test_client(),cm=value).status_code==400

@pytest.mark.parametrize("payload",[[],[1],"bad",42])
def test_non_object_json(payload):
    assert app.test_client().post('/api/readings',json=payload).status_code==400

def test_bad_calibration_and_identity():
    c=app.test_client()
    assert calibrate(c,full=30,empty=5).status_code==400
    assert c.put('/api/shelves/SHELF_01',json={'empty_cm':float('nan')}).status_code==400
    assert c.post('/api/readings',json=dict(device_id='wrong',shelf_id='SHELF_01',distance_cm=5)).status_code==400
    assert send(c,timestamp=12345).status_code==400

def test_recalibration_retains_history_and_waits_for_new_sample():
    c=app.test_client();calibrate(c);send(c)
    assert calibrate(c,full=6).status_code==200
    assert c.get('/api/shelves').json[0]['status']=='WAITING'
    assert len(c.get('/api/readings/SHELF_01/history').json)==1
    send(c,cm=6)
    assert c.get('/api/shelves').json[0]['status']=='FULL'

def test_same_timestamp_returns_one_latest_sample():
    c=app.test_client()
    timestamp=datetime.now(timezone.utc).isoformat()
    send(c,cm=5,timestamp=timestamp);send(c,cm=20,timestamp=timestamp)
    rows=c.get('/api/readings').json
    assert len(rows)==1 and rows[0]['sensor_value']==20

def test_dashboard_and_assets():
    c=app.test_client()
    for path in ['/', '/static/app.js', '/static/style.css']:
        assert c.get(path).status_code==200

def test_simulator_hardware_switch_resets_filter():
    c=app.test_client();calibrate(c)
    c.post('/api/readings',json=dict(device_id='ESP32_01',shelf_id='SHELF_01',sensor_type='simulated',distance_cm=30))
    r=send(c,cm=5)
    assert r.json['filtered_value']==5


def test_write_authentication(monkeypatch):
    import importlib
    module=importlib.import_module('backend.app')
    monkeypatch.setattr(module,'API_KEY','test-secret')
    c=app.test_client()
    payload=dict(device_id='ESP32_01',shelf_id='SHELF_01',distance_cm=5)
    assert c.post('/api/readings',json=payload).status_code==401
    assert c.post('/api/readings',json=payload,headers={'X-API-Key':'test-secret'}).status_code==201
    assert c.get('/api/shelves').status_code==200
