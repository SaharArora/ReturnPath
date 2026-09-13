import fcntl
import hashlib
import json
import os
import signal
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .policy import decide
from .storage import audit


@contextmanager
def ownership(path):
    with open(str(Path(path).resolve()) + ".worker.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Financial worker already owns this environment") from None
        yield


def barrier(path, boundary):
    # Harness creates an explicitly scoped boundary file; no public mutation route.
    arm = Path(str(path) + "." + boundary)
    if arm.exists():
        arm.unlink()
        Path(str(arm) + ".reached").touch()
        os.kill(os.getpid(), signal.SIGSTOP)


def tick(db, provider, now=None, fault_path=None):
    now = time.time() if now is None else now
    with db:
        db.execute("INSERT INTO heartbeats VALUES('worker',?) ON CONFLICT(component) DO UPDATE SET at=excluded.at", (now,))
    for case_row in db.execute("SELECT * FROM cases").fetchall():
        case = dict(case_row)
        cid = case["id"]
        op_row = db.execute("SELECT * FROM operations WHERE case_id=?", (cid,)).fetchone()
        op = dict(op_row) if op_row else None
        try:
            charge, refunds = provider.observe(case["charge"])
        except Exception:
            audit(db, cid, "PAYMENT_UNKNOWN", {}, now)
            continue
        if op:
            params = json.loads(op["params"])
            expected = {"charge": case["charge"], "amount": case["amount"], "currency": case["currency"], "policy": case["policy"]}
            if params != expected or hashlib.sha256(op["params"].encode()).hexdigest() != op["hash"]:
                with db:
                    db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
                continue
        matching = [r for r in refunds if op and r.get("operation") == op["id"]
                    and r.get("case_id") == cid and r.get("charge") == case["charge"]
                    and r.get("amount") == case["amount"] and r.get("currency") == case["currency"]]
        conflict = len(matching) > 1 or len(matching) != len(refunds)
        if op and op["provider_id"] and (not matching or matching[0]["id"] != op["provider_id"]):
            conflict = True
        if conflict:
            with db:
                db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
            audit(db, cid, "REFUND_CONFLICT", {"count": len(refunds)}, now)
            continue
        if matching:
            refund = matching[0]
            status = refund["status"]
            with db:
                db.execute("UPDATE operations SET provider_id=?,status=? WHERE id=?", (refund["id"], status, op["id"]))
                db.execute("UPDATE cases SET summary=? WHERE id=?", ("NOTIFICATION_PENDING" if status == "succeeded" else "PAYMENT_PENDING", cid))
                if status not in {"succeeded", "pending"}:
                    db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
            audit(db, cid, "PROVIDER_OBSERVED", {"status": status, "count": 1, "amount": refund["amount"]}, now)
            if status == "succeeded" and not case["hold"]:
                notify(db, provider, case, op, now, fault_path)
            continue
        authorized = db.execute("SELECT 1 FROM contacts WHERE case_id=? AND verified=1", (cid,)).fetchone() is not None
        facts = {"warehouse": None if case["warehouse"] is None else bool(case["warehouse"]),
                 "charge": charge, "refunds": refunds, "fetched_at": now,
                 "expected_charge": case["charge"], "approved": case["amount"]}
        decision = decide(facts, authorized, op, case["hold"], now)
        audit(db, cid, decision.reason, {"action": decision.action}, now)
        if decision.action == "REVIEW":
            with db:
                db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
        if decision.action != "POST":
            continue
        if op is None:
            oid = str(uuid.uuid4())
            params = json.dumps({"charge": case["charge"], "amount": case["amount"],
                                 "currency": case["currency"], "policy": case["policy"]}, sort_keys=True)
            with db:
                db.execute("INSERT INTO operations(id,case_id,params,hash,idem) VALUES(?,?,?,?,?)",
                           (oid, cid, params, hashlib.sha256(params.encode()).hexdigest(), "returnpath-refund:" + oid))
            op = dict(db.execute("SELECT * FROM operations WHERE id=?", (oid,)).fetchone())
        with db:
            db.execute("UPDATE operations SET first_attempt=coalesce(first_attempt,?), attempts=attempts+1, next_attempt=?,status='ATTEMPT_STARTED' WHERE id=?",
                       (now, now + 10 * 2 ** op["attempts"], op["id"]))
        if fault_path:
            barrier(fault_path, "before-post")
        try:
            result = provider.refund(op, json.loads(op["params"]))
            if fault_path:
                barrier(fault_path, "after-provider-success")
            with db:
                db.execute("UPDATE operations SET provider_id=? WHERE id=?", (result["id"], op["id"]))
        except Exception:
            audit(db, cid, "WRITE_UNKNOWN", {}, now)
        # Success is always established by a subsequent read, never this POST response.


def notify(db, provider, case, op, now, fault_path):
    key = "refund-status:" + op["id"]
    body = "Payment provider reports the approved $30.00 USD refund succeeded. Bank posting time may vary."
    with db:
        db.execute("INSERT OR IGNORE INTO notifications(id,case_id,recipient,body) VALUES(?,?,?,?)",
                   (key, case["id"], case["customer"], body))
    row = db.execute("SELECT * FROM notifications WHERE id=?", (key,)).fetchone()
    if row["state"] != "SUBMITTED":
        if row["state"] != "NOT_ATTEMPTED":
            try:
                found = provider.sent(key, row["recipient"], row["body"])
            except Exception:
                found = []
            if len(found) == 1:
                with db:
                    db.execute("UPDATE notifications SET state='SUBMITTED',provider_id=? WHERE id=?", (found[0]["id"], key))
            else:
                with db:
                    db.execute("UPDATE notifications SET state='SEND_UNKNOWN' WHERE id=?", (key,))
                return
        else:
            with db:
                db.execute("UPDATE notifications SET state='ATTEMPT_STARTED',attempted=? WHERE id=?", (now, key))
            try:
                mid = provider.send(key, row["recipient"], row["body"])
                if fault_path:
                    barrier(fault_path, "after-mail-success")
                with db:
                    db.execute("UPDATE notifications SET state='SUBMITTED',provider_id=? WHERE id=?", (mid, key))
            except Exception:
                with db:
                    db.execute("UPDATE notifications SET state='SEND_UNKNOWN' WHERE id=?", (key,))
                return
    try:
        provider.slack(case["id"], {"operation": op["id"], "refund": op["provider_id"],
                       "verified_fact": "Stripe/simulator reports $30 succeeded", "notification": "SUBMITTED",
                       "remaining": "No automatic financial action", "dashboard": "/cases/" + case["id"]})
    except Exception:
        audit(db, case["id"], "SLACK_UNKNOWN", {}, now)
        return
    with db:
        db.execute("UPDATE cases SET summary='RESOLVED' WHERE id=?", (case["id"],))
