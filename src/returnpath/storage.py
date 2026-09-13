import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS cases (
 id TEXT PRIMARY KEY, order_ref TEXT UNIQUE NOT NULL, customer TEXT NOT NULL,
 charge TEXT UNIQUE NOT NULL, original INTEGER NOT NULL CHECK(original=10000),
 amount INTEGER NOT NULL CHECK(amount=3000), currency TEXT NOT NULL CHECK(currency='usd'),
 policy TEXT NOT NULL, warehouse INTEGER, hold INTEGER NOT NULL DEFAULT 0,
 summary TEXT NOT NULL DEFAULT 'WAITING_FOR_VERIFICATION');
CREATE TABLE IF NOT EXISTS contacts (
 id TEXT PRIMARY KEY, channel TEXT NOT NULL, event TEXT NOT NULL,
 case_id TEXT REFERENCES cases(id), verified INTEGER NOT NULL DEFAULT 0,
 UNIQUE(channel,event));
CREATE TABLE IF NOT EXISTS verifications (
 digest TEXT PRIMARY KEY, contact TEXT NOT NULL REFERENCES contacts(id),
 case_id TEXT NOT NULL REFERENCES cases(id), capability TEXT NOT NULL,
 expires REAL NOT NULL, consumed REAL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS operations (
 id TEXT PRIMARY KEY, case_id TEXT UNIQUE NOT NULL REFERENCES cases(id),
 params TEXT NOT NULL, hash TEXT NOT NULL, idem TEXT UNIQUE NOT NULL,
 first_attempt REAL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
 provider_id TEXT, status TEXT NOT NULL DEFAULT 'NOT_ATTEMPTED');
CREATE TRIGGER IF NOT EXISTS immutable_operation BEFORE UPDATE OF id,case_id,params,hash,idem ON operations
 BEGIN SELECT RAISE(ABORT,'immutable operation'); END;
CREATE TRIGGER IF NOT EXISTS immutable_case BEFORE UPDATE OF id,order_ref,customer,charge,original,amount,currency,policy ON cases
 BEGIN SELECT RAISE(ABORT,'immutable approval'); END;
CREATE TABLE IF NOT EXISTS notifications (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), recipient TEXT NOT NULL,
 body TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'NOT_ATTEMPTED', attempted REAL, provider_id TEXT);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at REAL NOT NULL, case_id TEXT, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS heartbeats (component TEXT PRIMARY KEY, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, at REAL NOT NULL, state TEXT NOT NULL);
"""


def connect(path, *, agreement=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    schema = SCHEMA
    if agreement:
        schema = schema.replace("CHECK(original=10000)", "CHECK(original>0 AND original<=100000)").replace("CHECK(amount=3000)", "CHECK(amount>0 AND amount<=original)")
    db.executescript(schema)
    path.chmod(0o600)
    return db


def audit(db, case_id, kind, data, now):
    with db:
        db.execute("INSERT INTO audit(at,case_id,kind,data) VALUES(?,?,?,?)",
                   (now, case_id, kind, json.dumps(data, sort_keys=True)))
