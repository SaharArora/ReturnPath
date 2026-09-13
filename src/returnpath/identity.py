import hashlib
import secrets
import time
import uuid
from .storage import audit
from .interpreter import interpret


def ingest(db, c, event, text, channel="gmail", now=None):
    now = time.time() if now is None else now
    existing = db.execute("SELECT * FROM contacts WHERE channel=? AND event=?", (channel, event)).fetchone()
    if existing and existing["case_id"]:
        return existing["id"]
    cid = existing["id"] if existing else str(uuid.uuid4())
    with db:
        db.execute("INSERT OR IGNORE INTO contacts(id,channel,event) VALUES(?,?,?)", (cid, channel, event))
    if not existing:
        print("Gmail contact received; interpretation pending" if channel == "gmail" else "Contact received; interpretation pending", flush=True)
    stored = db.execute("SELECT id FROM contacts WHERE channel=? AND event=?", (channel, event)).fetchone()[0]
    if stored != cid:
        return stored
    db.execute("CREATE TABLE IF NOT EXISTS model_attempts (contact TEXT PRIMARY KEY, count INTEGER NOT NULL, next_at REAL NOT NULL)")
    db.commit()
    attempts = db.execute("SELECT * FROM model_attempts WHERE contact=?", (cid,)).fetchone()
    if attempts and (attempts["count"] >= 3 or now < attempts["next_at"]):
        return cid
    with db:
        db.execute("INSERT INTO model_attempts VALUES(?,1,?) ON CONFLICT(contact) DO UPDATE SET count=count+1,next_at=excluded.next_at", (cid, now + 30))
    # Durable call budget survives crashes. Input is re-read from allowlisted provider.
    try:
        if c.get('RP_MODE') == 'connected-test':
            from .limits import reserve
            reserve(db, 'model_calls', 20)
        result = interpret(c, text)
    except Exception as exc:
        # Exception messages may contain provider bodies or customer input.
        category = type(exc).__name__
        audit(db, None, "INTERPRETATION_UNKNOWN", {"contact": cid, "error_type": category}, now)
        print("Interpretation failed: " + category + "; bounded attempts recorded; no verification issued", flush=True)
        return cid
    case = None
    if result.intent in {"REFUND_STATUS", "RETURN_FOLLOWUP"} and result.order_reference:
        case = db.execute("SELECT id FROM cases WHERE order_ref=?", (result.order_reference,)).fetchone()
        if result.return_reference and (not case or result.return_reference != case[0]):
            case = None
    with db:
        db.execute("UPDATE contacts SET case_id=? WHERE id=?", (case[0] if case else None, cid))
    audit(db, case[0] if case else None, "INTERPRETATION", {"contact": cid, "intent": result.intent,
          "order_reference": result.order_reference, "clarification": result.clarification,
          "model": c.get("RP_MODEL") if c.get("RP_MODE") == "connected-test" else "DETERMINISTIC_STUB",
          "prompt_revision": "v1"}, now)
    print("Interpretation complete; " + ("case matched; verification required" if case else "no case matched"), flush=True)
    return cid


def issue(db, provider, contact, base_url, now=None):
    now = time.time() if now is None else now
    row = db.execute("SELECT c.id,c.case_id,c.verified,k.customer FROM contacts c JOIN cases k ON k.id=c.case_id WHERE c.id=?", (contact,)).fetchone()
    if not row or row["verified"]:
        return False
    recent = db.execute("SELECT count(*) FROM verifications WHERE case_id=? AND created>?", (row["case_id"], now - 3600)).fetchone()[0]
    prior = db.execute("SELECT created FROM verifications WHERE contact=? ORDER BY created DESC LIMIT 1", (contact,)).fetchone()
    if recent >= 3 or (prior and now - prior[0] < 60):
        return False
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with db:
        db.execute("UPDATE verifications SET expires=0 WHERE contact=? AND consumed IS NULL", (contact,))
        db.execute("INSERT INTO verifications VALUES(?,?,?,'refund-status',?,NULL,?)",
                   (digest, contact, row["case_id"], now + 900, now))
    # Secret only in trusted recipient email. Never journal/model/log URL.
    provider.send("verify:" + digest, row["customer"], "Confirm this contact's order status request on this Mac: " + base_url + "/verify/" + token)
    print("Verification email submitted to Gmail; awaiting customer confirmation", flush=True)
    return True


def challenge(db, token, now=None):
    now = time.time() if now is None else now
    if len(token) > 100:
        return None
    digest = hashlib.sha256(token.encode()).hexdigest()
    return db.execute("SELECT v.*,c.order_ref FROM verifications v JOIN cases c ON c.id=v.case_id WHERE digest=? AND expires>? AND consumed IS NULL AND capability='refund-status'", (digest, now)).fetchone()


def confirm(db, token, now=None):
    now = time.time() if now is None else now
    row = challenge(db, token, now)
    if not row:
        return False
    with db:
        changed = db.execute("UPDATE verifications SET consumed=? WHERE digest=? AND consumed IS NULL AND expires>?", (now, row["digest"], now)).rowcount
        if changed:
            db.execute("UPDATE contacts SET verified=1 WHERE id=? AND case_id=?", (row["contact"], row["case_id"]))
    return bool(changed)
