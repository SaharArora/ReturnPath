from returnpath.worker import tick
from returnpath.identity import ingest
from returnpath.config import Config


def test_slow_observation_cannot_authorize(world):
    db, p = world
    moment = [100]
    original = p.observe
    def slow(charge):
        result = original(charge)
        moment[0] += 31
        return result
    p.observe = slow
    tick(db, p, clock=lambda: moment[0])
    assert p.db.execute('SELECT count(*) FROM refunds').fetchone()[0] == 0


def test_review_hold_has_actionable_handoff(world):
    db, p = world
    with db:
        db.execute('UPDATE cases SET hold=1')
    tick(db, p, 100)
    text = p.db.execute('SELECT body FROM slack').fetchone()[0]
    assert 'REVIEW_HOLD' in text and 'replacement refund' in text


def test_model_retry_budget_durable(world, monkeypatch):
    import returnpath.identity as identity
    db, p = world
    calls = []
    def fail(*args):
        calls.append(1)
        raise TimeoutError()
    monkeypatch.setattr(identity, 'interpret', fail)
    c = Config({'RP_ENV_FILE': '/dev/null'})
    for now in [100, 101, 130, 160, 200]:
        ingest(db, c, 'retry', 'order 4127', now=now)
    assert len(calls) == 3
    assert db.execute("SELECT count(*) FROM contacts WHERE event='retry'").fetchone()[0] == 1


def test_F19_provider_sticky_error_replayed(world):
    db, p = world
    p.sticky_error = True
    tick(db, p, 100)
    p.sticky_error = False
    tick(db, p, 110)
    tick(db, p, 130)
    tick(db, p, 200)
    assert p.db.execute('SELECT count(*) FROM refunds').fetchone()[0] == 0
    assert db.execute('SELECT attempts FROM operations').fetchone()[0] == 3
    assert db.execute('SELECT hold FROM cases').fetchone()[0] == 1


def test_provider_key_expiry_can_duplicate_but_app_horizon_prevents_it(world):
    import json
    db, p = world
    moment = [100]
    p.clock = lambda: moment[0]
    tick(db, p, 100)
    op = dict(db.execute('SELECT * FROM operations').fetchone())
    moment[0] += 24 * 3600 + 1
    p.refund(op, json.loads(op['params']))  # Deliberate direct-provider bug probe.
    assert p.db.execute('SELECT count(*),sum(amount) FROM refunds').fetchone()[:] == (2,6000)
    tick(db, p, moment[0])
    assert db.execute('SELECT hold FROM cases').fetchone()[0] == 1


def test_dev_preserves_survivors_until_operator_interrupt(monkeypatch):
    import subprocess
    import returnpath.runtime as runtime
    children = []
    class Child:
        def __init__(self, component):
            self.component, self.terminated = component, False
        def poll(self):
            return -9 if self.component == 'worker' else None
        def terminate(self):
            self.terminated = True
        def wait(self, timeout):
            return 0
    def start(args):
        child = Child(args[-1])
        children.append(child)
        return child
    def stop(delay):
        assert not any(c.terminated for c in children)
        raise KeyboardInterrupt()
    monkeypatch.setattr(subprocess, 'Popen', start)
    monkeypatch.setattr(runtime.time, 'sleep', stop)
    runtime.dev(Config({'RP_ENV_FILE':'/dev/null'}))
    assert children[0].terminated and children[2].terminated


def test_daily_reservation_bound(world):
    import pytest
    from returnpath.limits import reserve
    db, _ = world
    reserve(db, 'synthetic', 1)
    with pytest.raises(ValueError):
        reserve(db, 'synthetic', 1)


def test_http_warehouse_requires_secret(tmp_path):
    from argon2 import PasswordHasher
    from fastapi.testclient import TestClient
    from returnpath.web import create_app
    from returnpath.warehouse import seed
    c = Config({'RP_ENV_FILE':'/dev/null','RP_STATE_DIR':str(tmp_path),
                'RP_OPERATOR_SESSION_SECRET':'s'*48,
                'RP_OPERATOR_PASSWORD_HASH':PasswordHasher().hash('synthetic-password')})
    app = create_app(c)
    seed(tmp_path / 'local/warehouse.sqlite', 'ret')
    client = TestClient(app)
    assert client.get('/warehouse/ret').status_code == 401
    data = client.get('/warehouse/ret', headers={'Authorization':'Bearer ' + 's'*48}).json()
    assert data['value'] is True and data['source'] == 'SIMULATED RETURN EVIDENCE'


def test_retry_after_is_durable_lower_bound(world):
    import stripe
    db, p = world
    calls = []
    def limited(*args):
        calls.append(1)
        raise stripe.RateLimitError('synthetic', headers={'Retry-After':'120'})
    p.refund = limited
    tick(db, p, 100)
    tick(db, p, 110)
    assert len(calls) == 1
    assert db.execute('SELECT next_attempt FROM operations').fetchone()[0] == 220
    tick(db, p, 220)
    assert len(calls) == 2
