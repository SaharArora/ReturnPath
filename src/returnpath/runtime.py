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
    from .warehouse import seed as seed_warehouse
    seed_warehouse(app.parent / 'warehouse.sqlite', "ret-4127-headphones")
    print("LOCAL SIMULATOR seeded; identity is fixture-preverified. $100 original / $30 approved")


def run(c, component, once=False):
    app, external = paths(c)
    db = connect(app)
    if c.get("RP_MODE", "local") == "connected-test":
        from .connected import Connected, SlackOnly
        provider = SlackOnly(c, db) if component == "watchdog" else Connected(c, db)
    else:
        provider = Fake(external)
    if c.get("RP_OPERATOR_SESSION_SECRET"):
        from .warehouse import http_observe
        provider.warehouse = lambda case_id: http_observe(c, case_id)
    next_gmail_poll = next_agreement_poll = 0
    poll_seconds = max(10, float(c.get("RP_GMAIL_POLL_SECONDS", "15")))
    agreement_db = agreement_provider = None
    agreement_path = app.parent / "agreement-app.sqlite"
    if component == "worker":
        with ownership(app):
            while True:
                if hasattr(provider, "intake") and time.monotonic() >= next_gmail_poll:
                    next_gmail_poll = time.monotonic() + poll_seconds
                    try:
                        provider.intake()
                    except Exception:
                        print("Intake/verification pending; inspect provider setup", flush=True)
                tick(db, provider, fault_path=app)
                if c.get('RP_MODE') == 'connected-test' and agreement_path.exists():
                    from .agreement_bridge import journal, AgreementConnected
                    if agreement_db is None:
                        agreement_db = journal(agreement_path)
                        agreement_provider = AgreementConnected(c, agreement_db)
                    if time.monotonic() >= next_agreement_poll:
                        next_agreement_poll = time.monotonic() + poll_seconds
                        try:
                            agreement_provider.intake()
                        except Exception as exc:
                            print('Agreement intake pending: ' + type(exc).__name__, flush=True)
                    tick(agreement_db, agreement_provider, fault_path=agreement_path)
                if once:
                    return
                time.sleep(1)
    else:
        while True:
            inspect(db, provider, stale=float(c.get("RP_WORKER_STALE_SECONDS", "20")))
            if c.get('RP_MODE') == 'connected-test' and agreement_path.exists():
                from .agreement_bridge import journal
                if agreement_db is None:
                    agreement_db = journal(agreement_path)
                    from .connected import SlackOnly
                    agreement_provider = SlackOnly(c, agreement_db)
                inspect(agreement_db, agreement_provider, stale=float(c.get("RP_WORKER_STALE_SECONDS", "20")))
            if once:
                return
            time.sleep(float(c.get("RP_WATCHDOG_POLL_SECONDS", "10")))


def dev(c):
    import subprocess
    import sys
    children = []
    try:
        for component in ('web', 'worker', 'watchdog'):
            children.append(subprocess.Popen([sys.executable, '-m', 'returnpath', component]))
        reported = set()
        while True:
            for index, child in enumerate(children):
                if child.poll() is not None and index not in reported:
                    reported.add(index)
                    print(('web', 'worker', 'watchdog')[index] + " stopped; surviving processes remain running. Operator restart required.", flush=True)
            if len(reported) == len(children):
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
