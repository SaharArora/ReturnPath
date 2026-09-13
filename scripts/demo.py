"""Genuine local process demonstration; no fabricated external-service evidence."""
import json
import datetime
from returnpath.evidence import fingerprints
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import uuid

root = Path(__file__).resolve().parents[1]
run = root / '.runtime' / ('demo-' + str(uuid.uuid4()))
env = {**os.environ, 'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'local', 'RP_ALLOW_CONNECTED_WRITES': 'false', 'RP_STATE_DIR': str(run),
       'RP_WORKER_STALE_SECONDS': '0.3', 'RP_WATCHDOG_POLL_SECONDS': '0.1'}
trace = []
started = time.monotonic()


def event(text):
    trace.append({'seconds': round(time.monotonic() - started, 3), 'event': text})
    print(text, flush=True)


def launch(command, once=False):
    return subprocess.Popen([sys.executable, '-m', 'returnpath', command] + (['--once'] if once else []), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for(predicate):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise RuntimeError('Demo synchronization deadline exceeded')


p = launch('seed')
assert p.wait(timeout=10) == 0
app = run / 'local/app.sqlite'
arm = Path(str(app) + '.after-provider-success')
arm.touch()
event('LOCAL SIMULATORS: $100 charge / $30 approved; fixture-preverified contact. No live model.')
worker = launch('worker')
watchdog = launch('watchdog')
try:
    wait_for(lambda: Path(str(arm) + '.reached').exists())
    with sqlite3.connect(app.parent / 'provider.sqlite') as external:
        assert external.execute('SELECT count(*),sum(amount) FROM refunds').fetchone() == (1, 3000)
    event('Independent simulator database shows one $30 refund; worker stopped before completion write.')
    os.kill(worker.pid, signal.SIGKILL)
    assert worker.wait(timeout=5) == -9
    event('Worker killed with SIGKILL. Watchdog remains independently running.')
    with sqlite3.connect(app) as db:
        db.execute("INSERT INTO contacts VALUES('duplicate-demo','email-fixture','followup','ret-4127-headphones',0)")
    event('Second synthetic contact persisted without resetting operation or provider database.')
    def alerted():
        with sqlite3.connect(app) as db:
            return db.execute("SELECT 1 FROM alerts WHERE id='WORKER_STALE' AND state='SUBMITTED'").fetchone()
    wait_for(alerted)
    event('Independent watchdog submitted simulator stale-worker alert; no automatic restart.')
    for _ in range(2):
        p = launch('worker', once=True)
        assert p.wait(timeout=10) == 0
    event('Harness explicitly restarted worker; existing refund retrieved and notification submitted.')
    with sqlite3.connect(app.parent / 'provider.sqlite') as external:
        count, amount = external.execute('SELECT count(*),sum(amount) FROM refunds').fetchone()
        mail_count = external.execute('SELECT count(*) FROM mail').fetchone()[0]
        assert (count, amount, mail_count) == (1, 3000, 1)
    event('Independent final oracle PASS: 1 refund, 3000 cents aggregate, 1 simulator outcome mail.')
    output = root / 'evidence'
    output.mkdir(exist_ok=True)
    (output / 'local-demo.json').write_text(json.dumps({'mode': 'local', 'recording': None,
        'run_id': run.name, 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
        'fingerprints': fingerprints(), 'trace': trace,
        'refund_count': count, 'aggregate_cents': amount, 'mail_count': mail_count}, indent=2) + '\n')
finally:
    for p in [worker, watchdog]:
        if p.poll() is None:
            p.kill()
        p.wait(timeout=5)
