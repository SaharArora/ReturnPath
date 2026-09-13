import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import pytest


def wait_for(predicate, processes=(), seconds=8):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return
        for p in processes:
            assert p.poll() is None, "child exited before synchronization barrier"
        time.sleep(0.02)
    raise AssertionError("synchronization deadline exceeded")


def launch(root, component, once=False, **overrides):
    env = {**os.environ, 'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'local',
           'RP_STATE_DIR': str(root), 'RP_ALLOW_CONNECTED_WRITES': 'false', **overrides}
    return subprocess.Popen([sys.executable, '-m', 'returnpath', component] + (['--once'] if once else []),
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def seeded(tmp_path):
    p = launch(tmp_path, 'seed')
    assert p.wait(timeout=8) == 0
    return tmp_path / 'local' / 'app.sqlite'


def cleanup(*processes):
    for p in processes:
        if p.poll() is None:
            p.kill()
        p.wait(timeout=5)


def test_F05_two_actual_workers(tmp_path):
    app = seeded(tmp_path)
    arm = Path(str(app) + '.before-post')
    arm.touch()
    first = launch(tmp_path, 'worker')
    try:
        wait_for(lambda: Path(str(arm) + '.reached').exists(), [first])
        second = launch(tmp_path, 'worker', once=True)
        assert second.wait(timeout=8) != 0
    finally:
        cleanup(first)


@pytest.mark.parametrize('boundary', ['before-post', 'after-provider-success'])
def test_F06_F08_sigkill_restart_duplicate_contact(tmp_path, boundary):
    app = seeded(tmp_path)
    arm = Path(str(app) + '.' + boundary)
    arm.touch()
    worker = launch(tmp_path, 'worker')
    try:
        wait_for(lambda: Path(str(arm) + '.reached').exists(), [worker])
        worker.kill()
        assert worker.wait(timeout=5) == -9
        with sqlite3.connect(app) as db:
            original = db.execute('SELECT id,idem,params FROM operations').fetchone()
            db.execute("INSERT INTO contacts VALUES('followup','email','second','ret-4127-headphones',0)")
            # Injectable durable retry schedule, never reset identity or provider records.
            db.execute('UPDATE operations SET next_attempt=0')
        for _ in range(2):
            p = launch(tmp_path, 'worker', once=True)
            assert p.wait(timeout=8) == 0
        with sqlite3.connect(app.parent / 'provider.sqlite') as external:
            rows = external.execute('SELECT amount,currency,charge FROM refunds').fetchall()
            assert rows == [(3000, 'usd', 'ch_fake_4127')]
            assert external.execute('SELECT count(*) FROM mail').fetchone()[0] == 1
        with sqlite3.connect(app) as db:
            assert db.execute('SELECT id,idem,params FROM operations').fetchone() == original
            assert db.execute('SELECT count(*) FROM contacts').fetchone()[0] == 2
    finally:
        cleanup(worker)


def test_F26_watchdog_survives_worker(tmp_path):
    app = seeded(tmp_path)
    arm = Path(str(app) + '.before-post')
    arm.touch()
    worker = launch(tmp_path, 'worker')
    watcher = None
    try:
        wait_for(lambda: Path(str(arm) + '.reached').exists(), [worker])
        watcher = launch(tmp_path, 'watchdog', RP_WORKER_STALE_SECONDS='0.2', RP_WATCHDOG_POLL_SECONDS='0.05')
        worker.kill()
        worker.wait(timeout=5)
        def alerted():
            with sqlite3.connect(app) as db:
                return db.execute("SELECT 1 FROM alerts WHERE id='WORKER_STALE' AND state='SUBMITTED'").fetchone()
        wait_for(alerted, [watcher])
        assert watcher.poll() is None
        with sqlite3.connect(app.parent / 'provider.sqlite') as external:
            assert external.execute("SELECT 1 FROM slack WHERE id='watchdog:WORKER_STALE'").fetchone()
    finally:
        cleanup(*([worker, watcher] if watcher else [worker]))
