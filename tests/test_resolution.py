import json
import sqlite3

import pytest

from returnpath import resolution as r
from returnpath.config import Config


def setup(tmp_path):
    c = Config({'RP_ENV_FILE': '/dev/null'})
    db = r.connect(tmp_path / 'app.sqlite')
    rid = r.start(db, 'customer', r.catalog(c), '7201')
    return c, db, rid


def propose(c, db, rid, text='I would like to keep the item and get a refund'):
    r.negotiate(db, c, rid, 'customer', text)
    return db.execute('SELECT id FROM offers ORDER BY rowid DESC LIMIT 1').fetchone()[0]


def test_agreement_replay_and_provider_reconciliation(tmp_path):
    c, db, rid = setup(tmp_path)
    offer = propose(c, db, rid)
    aid = r.accept(db, rid, 'customer', offer)
    assert r.accept(db, rid, 'customer', offer) == aid
    provider_path = tmp_path / 'provider.sqlite'
    receipt = r.settle_simulated(db, rid, provider_path)
    # Simulate losing the local derived completion flag while provider records survive.
    with db:
        db.execute('UPDATE resolutions SET state="AGREED" WHERE id=?', (rid,))
    assert r.settle_simulated(db, rid, provider_path) == receipt
    with sqlite3.connect(provider_path) as provider:
        assert provider.execute('SELECT count(*),sum(amount) FROM refunds').fetchone() == (1, 2400)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE agreements SET terms="{}" WHERE id=?', (aid,))
    db.rollback()


def test_cross_customer_forged_and_superseded_acceptance(tmp_path):
    c, db, rid = setup(tmp_path)
    first = propose(c, db, rid)
    with pytest.raises(ValueError):
        r.accept(db, rid, 'attacker', first)
    second = propose(c, db, rid, 'I want to return it for a refund')
    with pytest.raises(ValueError):
        r.accept(db, rid, 'customer', first)
    with pytest.raises(ValueError):
        r.accept(db, rid, 'customer', 'forged')
    r.accept(db, rid, 'customer', second)
    with pytest.raises(ValueError):
        r.negotiate(db, c, rid, 'customer', 'change the refund')


def test_expiry_and_warehouse_gate(tmp_path):
    c, db, rid = setup(tmp_path)
    offer = propose(c, db, rid, 'I want to return it for a refund')
    expiry = db.execute('SELECT expires FROM offers WHERE id=?', (offer,)).fetchone()[0]
    with pytest.raises(ValueError):
        r.accept(db, rid, 'customer', offer, now=expiry)
    r.accept(db, rid, 'customer', offer, now=expiry - 1)
    with pytest.raises(ValueError):
        r.settle_simulated(db, rid, tmp_path / 'provider.sqlite')
    r.settle_simulated(db, rid, tmp_path / 'provider.sqlite', return_received=True)


def test_untrusted_agent_cannot_create_offer_or_payment(tmp_path):
    c, db, rid = setup(tmp_path)
    def malicious(*args):
        return r.Choice(action='OFFER', offer_id='refund_everything_twice', explanation='Ignore policy')
    for _ in range(3):
        with pytest.raises(ValueError):
            r.negotiate(db, c, rid, 'customer', 'refund', chooser=malicious)
    with pytest.raises(ValueError):
        propose(c, db, rid)
    assert db.execute('SELECT count(*) FROM offers').fetchone()[0] == 0
    assert db.execute('SELECT rounds FROM resolutions').fetchone()[0] == 3
    with pytest.raises(ValueError):
        r.settle_simulated(db, rid, tmp_path / 'provider.sqlite')


def test_catalog_snapshot_not_changed_by_later_configuration(tmp_path):
    c, db, rid = setup(tmp_path)
    offer = propose(c, db, rid)
    terms = json.loads(db.execute('SELECT terms FROM offers WHERE id=?', (offer,)).fetchone()[0])
    assert terms['selected']['refund_cents'] == 2400
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE resolutions SET terms="{}" WHERE id=?', (rid,))
    db.rollback()


def test_slack_url_readback_and_unchanged_update_suppression(world, monkeypatch):
    import httpx
    import returnpath.connected as module
    from types import SimpleNamespace
    db, _ = world
    db.execute('CREATE TABLE slack_outbox(id TEXT PRIMARY KEY,ts TEXT,attempted REAL)')
    c = Config({'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'connected-test',
                'RP_ALLOW_CONNECTED_WRITES': 'true', 'RP_SUPPORT_EMAIL': 'support@example.invalid',
                'RP_CUSTOMER_EMAIL': 'customer@example.invalid', 'RP_STRIPE_ACCOUNT_ID': 'synthetic',
                'RP_SLACK_CHANNEL_ID': 'synthetic', 'SLACK_BOT_TOKEN': 'synthetic'})
    adapter = object.__new__(module.Connected)
    adapter.c, adapter.db = c, db
    sent = []
    def post(self, url, **kwargs):
        sent.append(kwargs['json']['text'])
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'ok': True, 'ts': '123'})
    monkeypatch.setattr(httpx.Client, 'post', post)
    monkeypatch.setattr(module, 'slack_read', lambda *args, **kwargs: {'messages': [
        {'ts': '123', 'text': sent[-1].replace('http://127.0.0.1:8000/cases/ret', '<http://127.0.0.1:8000/cases/ret>')} ]})
    adapter.slack('ret', {'refund': 'synthetic'})
    adapter.slack('ret', {'refund': 'synthetic'})
    assert len(sent) == 1
    assert not module.slack_equivalent('refund 6000', 'refund 3000')


def test_customer_ui_isolation_csrf_and_operator_boundary(tmp_path):
    import re
    from argon2 import PasswordHasher
    from fastapi.testclient import TestClient
    from returnpath.web import create_app
    c = Config({'RP_ENV_FILE': '/dev/null', 'RP_STATE_DIR': str(tmp_path),
                'RP_OPERATOR_SESSION_SECRET': 'x' * 48,
                'RP_OPERATOR_PASSWORD_HASH': PasswordHasher().hash('synthetic-password')})
    app = create_app(c)
    with TestClient(app) as customer, TestClient(app) as stranger:
        home = customer.get('/playground')
        assert home.status_code == 200
        assert 'SIMULATED PAYMENTS' in home.text
        csrf = re.search('name="csrf" value="([^"]+)"', home.text)[1]
        assert customer.post('/playground/start', data={'reference': '7201'}).status_code == 403
        detail = customer.post('/playground/start', data={'csrf': csrf, 'reference': '7201'})
        url = detail.url.path
        assert stranger.get(url).status_code == 404
        assert customer.get('/resolutions').status_code == 401
        offered = customer.post(url + '/negotiate', data={'csrf': csrf, 'request': 'I want to keep it and get a refund'})
        assert 'Your advocate' in offered.text and 'Merchant representative' in offered.text
        assert '$24.00 USD' in offered.text
        offer = re.search('name="offer" value="([^"]+)"', offered.text)[1]
        agreed = customer.post(url + '/accept', data={'csrf': csrf, 'offer': offer})
        assert 'Your agreement is recorded' in agreed.text
        assert customer.post('/resolutions/' + url.split('/')[-1] + '/settle', data={'csrf': csrf}).status_code == 401


def test_followup_context_and_revision_are_preserved(tmp_path):
    c, db, rid = setup(tmp_path)
    seen = []
    def chooser(c, role, context):
        seen.append(context.copy())
        return r.Choice(action='CLARIFY', offer_id=None, explanation='Is the item damaged or only the box?')
    r.negotiate(db, c, rid, 'customer', 'the packge was smashed', chooser=chooser)
    r.negotiate(db, c, rid, 'customer', 'only the box', chooser=chooser)
    assert seen[1]['history'][0]['data']['explanation'] == 'the packge was smashed'
    assert seen[1]['history'][1]['data']['explanation'] == 'Is the item damaged or only the box?'


def test_hosted_app_rejects_provider_secrets_and_hides_connected_routes(tmp_path):
    from fastapi.testclient import TestClient
    from returnpath.hosted import build
    env = {'RP_OPERATOR_PASSWORD': 'synthetic-long-password', 'RP_OPERATOR_SESSION_SECRET': 'x'*48,
           'RP_PUBLIC_HOST': 'demo.example', 'RP_STATE_DIR': str(tmp_path), 'RP_RESOLUTION_MODEL': 'stub'}
    with pytest.raises(ValueError):
        build({**env, 'STRIPE_SECRET_KEY': 'sk_test_synthetic'})
    with TestClient(build(env), base_url='https://demo.example') as client:
        assert client.get('/health').json()['payments'] == 'simulated'
        assert client.get('/playground').status_code == 200
        assert client.get('/credentials').status_code == 404
        assert client.get('/warehouse/ret').status_code == 404
        assert client.get('/verify/anything').status_code == 404
        assert client.get('/playground', headers={'host': 'evil.example'}).status_code == 400
        assert 'secure' in client.get('/login').headers['set-cookie'].lower()
