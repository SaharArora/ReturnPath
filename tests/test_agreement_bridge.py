import json
from types import SimpleNamespace as Obj

import pytest

from returnpath import resolution as r
from returnpath.agreement_bridge import journal, prepare, AgreementConnected, send_verification
from returnpath.config import Config
from returnpath.fake import Fake
from returnpath.identity import confirm
from returnpath.worker import tick


def world(tmp_path):
    c = Config({'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'connected-test', 'RP_ALLOW_CONNECTED_WRITES': 'true',
                'RP_CUSTOMER_EMAIL': 'customer@example.invalid', 'RP_SUPPORT_EMAIL': 'support@example.invalid',
                'RP_SLACK_CHANNEL_ID': 'channel', 'RP_STRIPE_ACCOUNT_ID': 'account'})
    resolutions = r.connect(tmp_path / 'resolutions.sqlite')
    rid = r.start(resolutions, 'customer-session', r.catalog(c), '7202')
    r.negotiate(resolutions, c, rid, 'customer-session', 'I want to keep the item and get a refund')
    offer = resolutions.execute('SELECT id FROM offers').fetchone()[0]
    r.accept(resolutions, rid, 'customer-session', offer)
    payments = journal(tmp_path / 'agreement-app.sqlite')
    calls = []
    def create(params, options):
        calls.append((params, options))
        return Obj(livemode=False, status='succeeded', latest_charge='ch_agreement')
    client = Obj(v1=Obj(accounts=Obj(retrieve_current=lambda: Obj(id='account')), payment_intents=Obj(create=create)))
    return c, resolutions, payments, rid, client, calls


def test_accepted_offer_requires_email_confirmation_then_exact_amount(tmp_path):
    c, resolutions, payments, rid, client, calls = world(tmp_path)
    cid = prepare(c, resolutions, payments, rid, client=client)
    assert calls[0][0]['amount'] == 6500
    assert prepare(c, resolutions, payments, rid, client=client) == cid
    assert len(calls) == 1
    provider = Fake(tmp_path / 'provider.sqlite')
    original_observe = provider.observe
    provider.observe = lambda charge: ({**original_observe(charge)[0], 'amount': 6500}, original_observe(charge)[1])
    check = object.__new__(AgreementConnected)
    check.db = payments
    provider.approval = check.approval
    provider.c = Config({**c.values, 'RP_BASE_URL': 'http://localhost/agreements'})
    tick(payments, provider)
    assert provider.db.execute('SELECT count(*) FROM refunds').fetchone()[0] == 0
    send_verification(payments, provider, cid)
    token = provider.db.execute('SELECT body FROM mail').fetchone()[0].split('/verify/')[1]
    assert confirm(payments, token)
    tick(payments, provider)
    tick(payments, provider)
    assert provider.db.execute('SELECT count(*),sum(amount) FROM refunds').fetchone()[:] == (1, 1500)
    body = provider.db.execute("SELECT body FROM mail WHERE semantic LIKE 'refund-status:%'").fetchone()[0]
    assert '$15.00 USD' in body
    # Repeated customer contact and lost cached completion must not create another refund.
    with payments:
        payments.execute('UPDATE cases SET summary="WAITING_FOR_VERIFICATION" WHERE id=?', (cid,))
        payments.execute('INSERT INTO contacts VALUES("followup","gmail","event2",?,0)', (cid,))
    tick(payments, provider)
    assert provider.db.execute('SELECT count(*) FROM refunds').fetchone()[0] == 1
    assert payments.execute('SELECT attempts FROM operations').fetchone()[0] == 1


def test_seed_ambiguity_never_creates_replacement(tmp_path):
    c, resolutions, payments, rid, client, calls = world(tmp_path)
    def fail(*args):
        raise TimeoutError()
    client.v1.payment_intents.create = fail
    with pytest.raises(TimeoutError):
        prepare(c, resolutions, payments, rid, client=client)
    with pytest.raises(ValueError, match='uncertain'):
        prepare(c, resolutions, payments, rid, client=client)
    assert payments.execute('SELECT count(*) FROM cases').fetchone()[0] == 0


def test_same_merchant_order_cannot_fund_second_agreement(tmp_path):
    c, resolutions, payments, rid, client, calls = world(tmp_path)
    prepare(c, resolutions, payments, rid, client=client)
    other = r.start(resolutions, 'other-session', r.catalog(c), '7202')
    r.negotiate(resolutions, c, other, 'other-session', 'keep it for a refund')
    offer = resolutions.execute('SELECT id FROM offers WHERE resolution=?', (other,)).fetchone()[0]
    r.accept(resolutions, other, 'other-session', offer)
    with pytest.raises(ValueError, match='another agreement'):
        prepare(c, resolutions, payments, other, client=client)
    assert len(calls) == 1


def test_adapter_posts_only_bound_accepted_amount(tmp_path):
    import sqlite3
    c, resolutions, payments, rid, client, calls = world(tmp_path)
    cid = prepare(c, resolutions, payments, rid, client=client)
    adapter = object.__new__(AgreementConnected)
    adapter.db, adapter.c = payments, c
    case = dict(payments.execute('SELECT * FROM cases').fetchone())
    assert adapter.approval(case) == (6500, 1500)
    with pytest.raises(ValueError):
        adapter.approval({**case, 'amount': 3000})
    params = {'charge': case['charge'], 'amount': 1500, 'currency': 'usd', 'policy': case['policy']}
    with payments:
        payments.execute('INSERT INTO operations(id,case_id,params,hash,idem,first_attempt,attempts) VALUES("op",?,?,"hash","key",1,1)', (cid, json.dumps(params)))
    op = dict(payments.execute('SELECT * FROM operations').fetchone())
    posted = []
    def refund(payload, options):
        posted.append(payload)
        return Obj(charge=case['charge'], amount=1500, currency='usd', id='re_15')
    adapter.stripe = Obj(v1=Obj(refunds=Obj(create=refund)))
    assert adapter.refund(op, params)['id'] == 're_15'
    assert posted[0]['amount'] == 1500
    with pytest.raises(ValueError):
        adapter.refund(op, {**params, 'amount': 3000})
    with pytest.raises(sqlite3.IntegrityError):
        payments.execute('UPDATE agreement_bindings SET terms="{}" WHERE case_id=?', (cid,))


def test_variable_agreement_survives_real_worker_kill(tmp_path):
    import os
    import sqlite3
    import subprocess
    import sys
    import time
    from pathlib import Path
    c, resolutions, payments, rid, client, calls = world(tmp_path)
    cid = prepare(c, resolutions, payments, rid, client=client)
    # Explicit local fixture grant; never used by connected verification routes.
    with payments:
        payments.execute('UPDATE contacts SET verified=1 WHERE case_id=?', (cid,))
    app = tmp_path / 'agreement-app.sqlite'
    provider = tmp_path / 'provider.sqlite'
    code = '''
import sys
from returnpath.isolation import install
install()
from returnpath.agreement_bridge import journal, AgreementConnected
from returnpath.fake import Fake
from returnpath.worker import tick, ownership
app,external=sys.argv[1:]
db=journal(app)
p=Fake(external)
observe=p.observe
p.observe=lambda charge: ({**observe(charge)[0], 'amount':6500},observe(charge)[1])
a=object.__new__(AgreementConnected)
a.db=db
p.approval=a.approval
with ownership(app):
    tick(db,p,fault_path=app)
'''
    arm = Path(str(app) + '.after-provider-success')
    arm.touch()
    env = {**os.environ, 'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'local', 'RP_ALLOW_CONNECTED_WRITES': 'false'}
    def launch():
        return subprocess.Popen([sys.executable, '-c', code, str(app), str(provider)], env=env)
    child = launch()
    try:
        deadline = time.monotonic() + 8
        while not Path(str(arm) + '.reached').exists():
            assert child.poll() is None
            assert time.monotonic() < deadline
            time.sleep(.02)
        child.kill()
        assert child.wait(timeout=5) == -9
        original = payments.execute('SELECT id,params,idem FROM operations').fetchone()[:]
        with payments:
            payments.execute('INSERT INTO contacts VALUES("crash-followup","gmail","repeat",?,0)', (cid,))
        resumed = launch()
        assert resumed.wait(timeout=8) == 0
        with sqlite3.connect(provider) as oracle:
            assert oracle.execute('SELECT count(*),sum(amount) FROM refunds').fetchone() == (1, 1500)
            assert oracle.execute('SELECT count(*) FROM mail').fetchone()[0] == 1
        assert payments.execute('SELECT id,params,idem FROM operations').fetchone()[:] == original
        assert payments.execute('SELECT attempts FROM operations').fetchone()[0] == 1
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
