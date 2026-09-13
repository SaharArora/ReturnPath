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


def tick(db, provider, now=None, fault_path=None, clock=None):
    clock = clock or (time.time if now is None else lambda: now)
    now = clock()
    with db:
        db.execute("INSERT INTO heartbeats VALUES('worker',?) ON CONFLICT(component) DO UPDATE SET at=excluded.at", (now,))
    for case_row in db.execute("SELECT * FROM cases").fetchall():
        case = dict(case_row)
        cid = case["id"]
        op_row = db.execute("SELECT * FROM operations WHERE case_id=?", (cid,)).fetchone()
        op = dict(op_row) if op_row else None
        observation_started = clock()
        try:
            charge, refunds = provider.observe(case["charge"])
        except Exception:
            audit(db, cid, "PAYMENT_UNKNOWN", {}, now)
            handoff(db, provider, cid, op, "PAYMENT_UNKNOWN", now)
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
            handoff(db, provider, cid, op, "REFUND_CONFLICT", now)
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
            if case["hold"]:
                with db:
                    db.execute("UPDATE cases SET summary='NEEDS_REVIEW' WHERE id=?", (cid,))
            if status == "succeeded" and not case["hold"]:
                notify(db, provider, case, op, now, fault_path)
            continue
        authorized = db.execute("SELECT 1 FROM contacts WHERE case_id=? AND verified=1", (cid,)).fetchone() is not None
        warehouse = None if case["warehouse"] is None else bool(case["warehouse"])
        if hasattr(provider, "warehouse"):
            try:
                warehouse = provider.warehouse(cid)
            except Exception:
                warehouse = None
        facts = {"warehouse": warehouse,
                 "charge": charge, "refunds": refunds, "fetched_at": observation_started,
                 "expected_charge": case["charge"], "approved": case["amount"]}
        now = clock()
        authority = {}
        if hasattr(provider, 'approval'):
            try:
                original, approved = provider.approval(case)
                authority = {'original': original, 'approved': approved}
            except Exception:
                with db:
                    db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
                audit(db, cid, "AGREEMENT_AUTHORITY_CONFLICT", {}, now)
                continue
        decision = decide(facts, authorized, op, case["hold"], now, **authority)
        audit(db, cid, decision.reason, {"action": decision.action}, now)
        if decision.action == "REVIEW":
            with db:
                db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
        if decision.action != "POST":
            if decision.action == "REVIEW" or "UNKNOWN" in decision.reason:
                handoff(db, provider, cid, op, decision.reason, now)
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
        except ValueError:
            with db:
                db.execute("UPDATE cases SET hold=1,summary='NEEDS_REVIEW' WHERE id=?", (cid,))
            audit(db, cid, "WRITE_REQUIRES_REVIEW", {}, now)
        except Exception as exc:
            # HTTP Retry-After is a lower bound; it never extends financial authority.
            headers = getattr(exc, 'headers', None) or {}
            retry_after = headers.get('Retry-After') or headers.get('retry-after')
            if retry_after:
                try:
                    delay = float(retry_after)
                except (ValueError, TypeError):
                    from email.utils import parsedate_to_datetime
                    try:
                        delay = parsedate_to_datetime(retry_after).timestamp() - now
                    except (ValueError, TypeError, OverflowError):
                        delay = 60
                import math
                if not math.isfinite(delay) or delay < 0:
                    delay = 60
                with db:
                    db.execute('UPDATE operations SET next_attempt=max(next_attempt,?) WHERE id=?', (now + delay, op['id']))
            audit(db, cid, "WRITE_UNKNOWN", {}, now)
        # Success is always established by a subsequent read, never this POST response.


def notify(db, provider, case, op, now, fault_path):
    key = "refund-status:" + op["id"]
    body = f"Payment provider reports the approved ${case['amount'] / 100:.2f} USD refund succeeded. Bank posting time may vary."
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
                       "verified_fact": f"Payment provider reports ${case['amount'] / 100:.2f} USD succeeded", "notification": "SUBMITTED",
                       "remaining": "No automatic financial action", "dashboard": "/cases/" + case["id"]})
    except Exception:
        audit(db, case["id"], "SLACK_UNKNOWN", {}, now)
        return
    with db:
        db.execute("UPDATE cases SET summary='RESOLVED' WHERE id=?", (case["id"],))


def handoff(db, provider, case_id, operation, reason, now):
    try:
        provider.slack(case_id, {"reason": reason, "operation": operation["id"] if operation else None,
                       "verified_facts": "Approval is fixed in trusted case records; provider success not assumed",
                       "unknown_or_conflict": reason, "action": "Inspect evidence and provider state; do not create a replacement refund",
                       "dashboard": "/cases/" + case_id})
    except Exception:
        audit(db, case_id, "SLACK_REVIEW_PENDING", {"reason": reason}, now)
