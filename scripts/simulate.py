"""Clearly labeled simulator, uses exactly the ESP32 HTTP ingest API."""
import argparse
import json
import math
import os
import time
import urllib.request
import urllib.error

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--url', default='http://127.0.0.1:5000')
p.add_argument('--scenario', choices=['cycle', 'full', 'low', 'empty', 'fault'], default='cycle')
p.add_argument('--cycles', type=int, default=0, help='0 means run until Ctrl+C')
p.add_argument('--interval', type=float, default=2)
p.add_argument('--calibrate-demo', action='store_true', help='Overwrites calibration with synthetic 5/30 cm values')
a = p.parse_args()
headers = {'Content-Type': 'application/json', 'X-API-Key': os.getenv('STOREWATCH_API_KEY', '')}
def send(path, payload, method='POST'):
    req = urllib.request.Request(a.url.rstrip('/') + path, json.dumps(payload).encode(), headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)
if a.calibrate_demo:
    try:
        for n in range(1, 4):
            send(f'/api/shelves/SHELF_0{n}', {'full_cm': 5, 'empty_cm': 30, 'low_percent': 25}, 'PUT')
    except (urllib.error.URLError, TimeoutError) as e:
        p.exit(1, f'Calibration failed: {e}. Start python -m backend.app first and verify the URL/key.\n')
    print('Synthetic calibration applied. Recalibrate before using physical sensors.')
print('SIMULATOR: all telemetry is labeled simulated; stop this before connecting ESP32.')
try:
    cycle = 0
    while not a.cycles or cycle < a.cycles:
        for n in range(1, 4):
            cm = {'full': 5, 'low': 26, 'empty': 30, 'fault': -1}.get(a.scenario)
            if cm is None:
                cm = 5 + 25 * (1 + math.sin(cycle / 6 + n * 2)) / 2
            payload = {'device_id': 'ESP32_01', 'shelf_id': f'SHELF_0{n}', 'sensor_type': 'simulated', 'distance_cm': round(cm, 2)}
            try:
                r = send('/api/readings', payload)
                print(f"{payload['shelf_id']} {cm:.1f} cm -> {r['status']}")
            except (urllib.error.URLError, TimeoutError) as e:
                print(f'Backend unavailable: {e}')
        cycle += 1
        if not a.cycles or cycle < a.cycles:
            time.sleep(max(0.1, a.interval))
except KeyboardInterrupt:
    print('\nSimulator stopped. Shelves become OFFLINE after 60 seconds.')
