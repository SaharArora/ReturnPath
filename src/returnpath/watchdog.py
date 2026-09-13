"""Independent detector/alerter. Never restarts the worker or invokes the planner."""
import time


def inspect(db, provider, now=None, stale=20):
    now = time.time() if now is None else now
    with db:
        db.execute("INSERT INTO heartbeats VALUES('watchdog',?) ON CONFLICT(component) DO UPDATE SET at=excluded.at", (now,))
    heartbeat = db.execute("SELECT at FROM heartbeats WHERE component='worker'").fetchone()
    reasons = []
    if heartbeat is None or now - heartbeat[0] > stale:
        reasons.append("WORKER_STALE")
    if db.execute("SELECT 1 FROM operations WHERE first_attempt < ? AND status != 'succeeded'", (now - 120,)).fetchone():
        reasons.append("FINANCIAL_ATTEMPT_OVERDUE")
    if db.execute("SELECT 1 FROM notifications WHERE state != 'SUBMITTED' AND attempted < ?", (now - 120,)).fetchone():
        reasons.append("NOTIFICATION_OVERDUE")
    for reason in reasons:
        with db:
            db.execute("INSERT OR IGNORE INTO alerts VALUES(?,?,'PENDING')", (reason, now))
        if db.execute("SELECT state FROM alerts WHERE id=?", (reason,)).fetchone()[0] == "SUBMITTED":
            continue
        try:
            provider.slack("watchdog:" + reason, {"reason": reason, "action": "Inspect protected dashboard and worker; operator restarts worker", "automatic_restart": False})
            with db:
                db.execute("UPDATE alerts SET state='SUBMITTED' WHERE id=?", (reason,))
        except Exception:
            print("Watchdog alert pending: " + reason, flush=True)
    return reasons
