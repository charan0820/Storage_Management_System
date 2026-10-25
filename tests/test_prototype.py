"""Regression checks for the two-row hardware prototype contract."""
import sqlite3
import pytest
from backend.app import app
from backend.database import db


def sample(client, row='SHELF_01', cm=30, **extra):
    return client.post('/api/readings', json={'device_id':'ESP32_01','shelf_id':row,
        'sensor_id':'US_01' if row=='SHELF_01' else 'US_02',
        'sensor_type':'ultrasonic','distance_cm':cm, **extra})


def test_manifest_tracks_assignment_and_persists():
    client=app.test_client()
    rows=client.get('/api/devices/ESP32_01/config').json['rows']
    assert [(r['parent_shelf'],r['row_number'],r['sensor_id']) for r in rows] == [
        ('RACK_01',1,'US_01'),('RACK_01',2,'US_02')]
    result=client.put('/api/shelves/SHELF_01',json={'product':'Rice packets','product_tag':'RICE-1'})
    assert result.status_code==200
    db.init_db()
    rows=client.get('/api/devices/ESP32_01/config').json['rows']
    assert rows[0]['product_tag']=='RICE-1' and rows[0]['product']=='Rice packets'
    assert rows[1]['product_tag']=='BIS-002'
    assert client.get('/api/devices/missing/config').status_code==404


def test_stale_device_tag_and_wrong_sensor_rejected():
    client=app.test_client()
    assert sample(client,product_tag='TEA-001').status_code==201
    assert sample(client,product_tag='OTHER').status_code==400
    assert sample(client,sensor_id='US_02').status_code==400
    assert len(client.get('/api/readings/SHELF_01/history').json)==1


def test_unknown_retired_and_boolean_telemetry_rejected():
    client=app.test_client()
    assert sample(client,row='SHELF_03').status_code==400
    assert sample(client,row='NOT_REGISTERED').status_code==400
    assert sample(client,cm=True).status_code==400


@pytest.mark.parametrize('tag',['','bad tag','<script>','x'*65,[],None])
def test_invalid_tags_return_400(tag):
    assert app.test_client().put('/api/shelves/SHELF_01',json={'product_tag':tag}).status_code==400


def test_reassignment_clears_old_alert_and_preserves_history():
    client=app.test_client()
    client.put('/api/shelves/SHELF_01',json={'full_cm':5,'empty_cm':30})
    assert sample(client).json['status']=='EMPTY'
    assert len(client.get('/api/alerts').json)==1
    client.put('/api/shelves/SHELF_01',json={'product':'Rice','product_tag':'RICE-1'})
    assert client.get('/api/alerts').json==[]
    assert client.get('/api/shelves').json[0]['status']=='WAITING'
    assert len(client.get('/api/readings/SHELF_01/history').json)==1
    assert sample(client,cm=5,product_tag='RICE-1').json['filtered_value']==5


def test_demo_calibration_is_explicit_and_can_be_replaced():
    client=app.test_client()
    client.put('/api/shelves/SHELF_01',json={'full_cm':5,'empty_cm':30,'calibration_source':'demo'})
    sample(client,cm=5)
    row=client.get('/api/shelves').json[0]
    assert row['calibration_source']=='demo' and row['fill_percent']==100
    assert client.put('/api/shelves/SHELF_01',json={'calibration_source':'invalid'}).status_code==400
    client.put('/api/shelves/SHELF_01',json={'full_cm':6,'empty_cm':29,'calibration_source':'measured'})
    assert client.get('/api/shelves').json[0]['calibration_source']=='measured'


def test_old_database_migration_retains_assignments_and_history(tmp_path,monkeypatch):
    path=tmp_path/'legacy.db'
    conn=sqlite3.connect(path)
    conn.executescript(db.SCHEMA)
    conn.execute("INSERT INTO shelves(shelf_id, product, device_id, calibrated) VALUES('SHELF_01','Existing product','ESP32_01',1)")
    conn.execute("INSERT INTO shelves(shelf_id, product, device_id) VALUES('SHELF_03','Retired product','ESP32_01')")
    conn.execute("INSERT INTO sensor_readings(device_id,shelf_id,sensor_type,sensor_value,filtered_value,status,timestamp) VALUES('ESP32_01','SHELF_03','simulated',10,10,'NORMAL','2026-09-01T00:00:00+00:00')")
    conn.commit();conn.close()
    monkeypatch.setattr(db,'DB_PATH',path)
    db.init_db();db.init_db()
    rows=app.test_client().get('/api/shelves').json
    assert len(rows)==2 and rows[0]['product']=='Existing product'
    assert rows[0]['product_tag']=='EXISTING-PRODUCT-001'
    assert rows[0]['calibration_source']=='demo'
    assert len(app.test_client().get('/api/readings/SHELF_03/history').json)==1


def test_setup_assets_and_path_allowlist():
    client=app.test_client()
    for path in ['/setup-guide','/hardware/hardware.md','/hardware/wiring.svg','/hardware/prototype.svg']:
        assert client.get(path).status_code==200
    assert client.get('/hardware/config.yaml').status_code==404


def test_backdated_telemetry_does_not_open_current_alert():
    from datetime import datetime,timedelta,timezone
    client=app.test_client()
    client.put('/api/shelves/SHELF_01',json={'full_cm':5,'empty_cm':30})
    old=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat()
    assert sample(client,timestamp=old).status_code==201
    assert client.get('/api/alerts').json==[]


def test_historical_import_does_not_pollute_live_filter():
    from datetime import datetime,timedelta,timezone
    client=app.test_client()
    client.put('/api/shelves/SHELF_01',json={'full_cm':5,'empty_cm':30})
    sample(client,cm=5)
    old=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat()
    sample(client,cm=30,timestamp=old)
    assert sample(client,cm=5).json['filtered_value']==5


def test_history_import_cannot_replace_a_fresh_live_sample():
    from datetime import datetime,timedelta,timezone
    client=app.test_client()
    client.put('/api/shelves/SHELF_01',json={'full_cm':5,'empty_cm':30})
    sample(client,cm=5)
    old=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat()
    sample(client,cm=30,timestamp=old)
    assert client.get('/api/shelves').json[0]['status']=='FULL'
    assert client.get('/api/readings/SHELF_01').json['sensor_value']==5
    history=client.get('/api/readings/SHELF_01/history').json
    assert [r['sensor_value'] for r in history]==[30,5]
