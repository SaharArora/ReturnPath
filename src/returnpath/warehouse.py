"""SIMULATED RETURN EVIDENCE, persisted independently from the operation journal."""
import sqlite3
import time
import httpx


def seed(path, case_id):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS warehouse (case_id TEXT PRIMARY KEY, accepted INTEGER)')
        db.execute('INSERT OR IGNORE INTO warehouse VALUES(?,1)', (case_id,))


def observe(path, case_id):
    with sqlite3.connect(path) as db:
        row = db.execute('SELECT accepted FROM warehouse WHERE case_id=?', (case_id,)).fetchone()
    return {'state': 'KNOWN' if row and row[0] is not None else 'UNKNOWN',
            'value': bool(row[0]) if row and row[0] is not None else None,
            'source': 'SIMULATED RETURN EVIDENCE', 'fetched_at': time.time()}


def http_observe(c, case_id):
    port = int(c.get('RP_WEB_PORT', '8000'))
    with httpx.Client(timeout=10) as client:
        response = client.get(f'http://127.0.0.1:{port}/warehouse/' + case_id,
            headers={'Authorization': 'Bearer ' + c.get('RP_OPERATOR_SESSION_SECRET')})
        response.raise_for_status()
        data = response.json()
    if data.get('state') != 'KNOWN' or type(data.get('value')) is not bool:
        return None
    if not 0 <= time.time() - data['fetched_at'] <= 30:
        return None
    return data['value']
