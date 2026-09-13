import time
import uuid

from .fake import Fake
from .storage import connect
from .watchdog import inspect
from .worker import ownership, tick


def paths(c):
    root = c.path_value("RP_STATE_DIR", "~/.local/share/returnpath") / c.get("RP_MODE", "local")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / "app.sqlite", root / "provider.sqlite"


def seed(c):
    if c.get("RP_MODE", "local") != "local":
        raise ValueError("Local seed cannot mutate connected state")
    app, provider = paths(c)
    db = connect(app)
    if db.execute("SELECT 1 FROM cases").fetchone():
        raise ValueError("Run already exists; restart without seeding. Use a fresh RP_STATE_DIR for a new rehearsal")
    with db:
        db.execute("INSERT INTO cases(id,order_ref,customer,charge,original,amount,currency,policy,warehouse) VALUES(?,?,?,?,10000,3000,'usd','v1',1)",
                   ("ret-4127-headphones", "4127", "customer@example.invalid", "ch_fake_4127"))
        db.execute("INSERT INTO contacts VALUES(?, 'fixture', 'seed', 'ret-4127-headphones',1)", (str(uuid.uuid4()),))
    Fake(provider)
    print("LOCAL SIMULATOR seeded; identity is fixture-preverified. $100 original / $30 approved")


def run(c, component, once=False):
    app, external = paths(c)
    if c.get("RP_MODE", "local") != "local":
        raise ValueError("Connected runtime not enabled until adapter contract checks pass")
    db = connect(app)
    provider = Fake(external)
    if component == "worker":
        with ownership(app):
            while True:
                tick(db, provider, fault_path=app)
                if once:
                    return
                time.sleep(1)
    else:
        while True:
            inspect(db, provider, stale=float(c.get("RP_WORKER_STALE_SECONDS", "20")))
            if once:
                return
            time.sleep(float(c.get("RP_WATCHDOG_POLL_SECONDS", "10")))
