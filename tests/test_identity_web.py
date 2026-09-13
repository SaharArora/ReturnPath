import re
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from returnpath.config import Config
from returnpath.identity import ingest, issue, challenge, confirm
from returnpath.interpreter import validate
from returnpath.web import create_app
import pytest


def test_F04_F20_contact_scope_expiry_replay(world):
    db, provider = world
    c = Config({'RP_ENV_FILE': '/dev/null'})
    contact = ingest(db, c, 'voice-event', 'refund for order 4127', channel='voice', now=100)
    assert db.execute('SELECT verified FROM contacts WHERE id=?', (contact,)).fetchone()[0] == 0
    assert issue(db, provider, contact, 'http://127.0.0.1:8000', now=100)
    body = provider.db.execute('SELECT body FROM mail').fetchone()[0]
    token = body.split('/verify/')[1]
    assert challenge(db, token, 101)
    assert challenge(db, token, 101)  # landing GET does not consume
    assert not confirm(db, 'bad', 101)
    assert confirm(db, token, 101)
    assert not confirm(db, token, 102)
    assert not challenge(db, token, 10000)


def test_F21_wrong_ambiguous_claimed_email(world):
    db, p = world
    c = Config({'RP_ENV_FILE': '/dev/null'})
    for event, text in [('wrong', 'order 9876 refund'), ('ambiguous', 'order 4127 or order 9876')]:
        contact = ingest(db, c, event, text)
        assert db.execute('SELECT case_id FROM contacts WHERE id=?', (contact,)).fetchone()[0] is None
        assert not issue(db, p, contact, 'http://localhost')


def test_F22_hostile_model_output():
    data = {'intent': 'REFUND_STATUS', 'order_reference': '4127', 'return_reference': None,
            'missing_fields': [], 'clarification': None, 'source_spans': ['4127']}
    with pytest.raises(ValueError):
        validate({**data, 'verified': True}, 'order 4127')
    with pytest.raises(ValueError):
        validate(data, 'order 9876')
    with pytest.raises(ValueError):
        validate(data, 'order 14127')


def test_F23_model_outage_no_binding(world, monkeypatch):
    import returnpath.identity as identity
    def fail(*args):
        raise TimeoutError()
    monkeypatch.setattr(identity, 'interpret', fail)
    db, p = world
    cid = ingest(db, Config({'RP_ENV_FILE': '/dev/null'}), 'outage', 'order 4127')
    assert db.execute('SELECT case_id FROM contacts WHERE id=?', (cid,)).fetchone()[0] is None


def test_F29_operator_auth_and_scoped_confirmation(tmp_path):
    c = Config({'RP_ENV_FILE': '/dev/null', 'RP_STATE_DIR': str(tmp_path),
                'RP_OPERATOR_SESSION_SECRET': 'x' * 48,
                'RP_OPERATOR_PASSWORD_HASH': PasswordHasher().hash('synthetic-password')})
    app = create_app(c)
    client = TestClient(app)
    assert client.get('/credentials').status_code == 200
    assert client.get('/authorization').status_code == 200
    assert client.get('/').status_code == 401
    assert client.get('/cases/ret').status_code == 401
    assert client.post('/login', data={'password': 'synthetic-password'}).status_code == 403
    landing = client.get('/login')
    csrf = re.search('name="csrf" value="([^"]+)"', landing.text)[1]
    assert client.post('/login', data={'csrf': csrf, 'password': 'synthetic-password'}).status_code == 200
    assert client.get('/').status_code == 200
    assert client.post('/fault').status_code == 404
    assert client.get('/', headers={'host': 'evil.example'}).status_code == 400
    assert client.get('/').headers['referrer-policy'] == 'no-referrer'
