"""Persistent SIMULATED providers. Separate database survives application death."""
import json
import sqlite3
import uuid


class Fake:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS refunds(id TEXT PRIMARY KEY, charge TEXT, amount INTEGER,
        currency TEXT, operation TEXT, case_id TEXT, idem TEXT UNIQUE, status TEXT);
        CREATE TABLE IF NOT EXISTS mail(id TEXT PRIMARY KEY, semantic TEXT, recipient TEXT, body TEXT);
        CREATE TABLE IF NOT EXISTS slack(id TEXT PRIMARY KEY, body TEXT);
        """)

    def observe(self, charge):
        return ({"id": charge, "amount": 10000, "currency": "usd", "livemode": False,
                 "paid": True, "captured": True, "disputed": False, "type": "card"},
                [dict(r) for r in self.db.execute("SELECT * FROM refunds WHERE charge=?", (charge,))])

    def refund(self, op, params):
        with self.db:
            existing = self.db.execute("SELECT * FROM refunds WHERE idem=?", (op["idem"],)).fetchone()
            if existing:
                if any(existing[k] != params[k] for k in ("charge", "amount", "currency")):
                    raise ValueError("Idempotency parameter conflict")
                return dict(existing)
            total = self.db.execute("SELECT coalesce(sum(amount),0) FROM refunds WHERE charge=?", (params["charge"],)).fetchone()[0]
            if total + params["amount"] > 10000:
                raise ValueError("Charge ceiling")
            rid = "re_fake_" + uuid.uuid4().hex
            self.db.execute("INSERT INTO refunds VALUES(?,?,?,?,?,?,?,?)", (rid, params["charge"],
                params["amount"], params["currency"], op["id"], op["case_id"], op["idem"], "succeeded"))
        return {"id": rid}

    def sent(self, semantic, recipient, body):
        return [dict(r) for r in self.db.execute("SELECT * FROM mail WHERE semantic=? AND recipient=? AND body=?",
                                               (semantic, recipient, body))]

    def send(self, semantic, recipient, body):
        mid = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO mail VALUES(?,?,?,?)", (mid, semantic, recipient, body))
        return mid

    def slack(self, case, data):
        with self.db:
            self.db.execute("INSERT INTO slack VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                            (case, json.dumps(data, sort_keys=True)))
