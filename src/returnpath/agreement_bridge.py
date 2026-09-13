"""Accepted merchant terms -> identity confirmation -> existing guarded TEST executor."""
import hashlib
import json
import time

from . import resolution
from .auth import stripe_client
from .connected import Connected
from .identity import issue
from .storage import connect


def journal(path):
    db = connect(path, agreement=True)
    db.executescript('''
    CREATE TABLE IF NOT EXISTS agreement_bindings(
      case_id TEXT PRIMARY KEY, agreement_id TEXT UNIQUE NOT NULL, resolution_id TEXT UNIQUE NOT NULL,
      order_ref TEXT UNIQUE NOT NULL, terms TEXT NOT NULL, customer TEXT NOT NULL,
      seed_started REAL NOT NULL, charge TEXT, return_received INTEGER NOT NULL DEFAULT 0);
    CREATE TRIGGER IF NOT EXISTS immutable_binding BEFORE UPDATE OF case_id,agreement_id,resolution_id,order_ref,terms,customer,seed_started ON agreement_bindings
      BEGIN SELECT RAISE(ABORT,'Immutable agreement authority'); END;
    CREATE TRIGGER IF NOT EXISTS immutable_bound_charge BEFORE UPDATE OF charge ON agreement_bindings
      WHEN OLD.charge IS NOT NULL
      BEGIN SELECT RAISE(ABORT,'Immutable bound charge'); END;
    ''')
    return db


def validate_terms(terms):
    order = resolution.Order.model_validate(terms['order'])
    selected = resolution.Offer.model_validate(terms['selected'])
    if terms['currency'] != 'usd' or selected.model_dump() not in [o.model_dump() for o in order.offers]:
        raise ValueError('Selected offer is outside merchant authority')
    if not 0 < selected.refund_cents <= order.paid_cents <= 100000:
        raise ValueError('Unsupported payment amount')
    return order, selected


def prepare(c, resolutions, payments, rid, receipt=False, client=None):
    c.writes()
    if c.get('RP_HOSTED') == 'true':
        raise ValueError('Hosted playground cannot prepare connected payments')
    accepted = resolutions.execute('SELECT * FROM agreements WHERE resolution=?', (rid,)).fetchone()
    if not accepted:
        raise ValueError('Customer must first accept exact terms')
    terms = json.loads(accepted['terms'])
    order, selected = validate_terms(terms)
    cid = 'agreement-' + accepted['id']
    prior = payments.execute('SELECT * FROM agreement_bindings WHERE order_ref=?', (order.reference,)).fetchone()
    if prior:
        if prior['agreement_id'] != accepted['id'] or prior['terms'] != accepted['terms']:
            raise ValueError('This merchant order is already bound to another agreement')
        if not prior['charge']:
            raise ValueError('TEST payment attempt uncertain; inspect Stripe before recovery. Do not reseed.')
        return cid
    client = client or stripe_client(c)
    if client.v1.accounts.retrieve_current().id != c.get('RP_STRIPE_ACCOUNT_ID'):
        raise ValueError('Stripe account mismatch')
    # Unique order reservation commits before provider creation. No replacement charge on ambiguity.
    with payments:
        payments.execute('INSERT INTO agreement_bindings VALUES(?,?,?,?,?,?,?,NULL,?)',
                         (cid, accepted['id'], rid, order.reference, accepted['terms'], c.get('RP_CUSTOMER_EMAIL'), time.time(), int(receipt)))
    pi = client.v1.payment_intents.create(
        {'amount': order.paid_cents, 'currency': 'usd', 'payment_method': 'pm_card_visa',
         'payment_method_types': ['card'], 'confirm': True,
         'metadata': {'returnpath_agreement': accepted['id'], 'case_id': cid}},
        {'idempotency_key': 'returnpath-agreement-seed:' + accepted['id']})
    if pi.livemode is not False or pi.status != 'succeeded' or not pi.latest_charge:
        raise ValueError('TEST payment outcome not verified')
    with payments:
        payments.execute('UPDATE agreement_bindings SET charge=? WHERE case_id=?', (pi.latest_charge, cid))
        payments.execute('INSERT INTO cases(id,order_ref,customer,charge,original,amount,currency,policy,warehouse) VALUES(?,?,?,?,?,?,?, ?,?)',
                         (cid, order.reference, c.get('RP_CUSTOMER_EMAIL'), pi.latest_charge,
                          order.paid_cents, selected.refund_cents, 'usd', 'agreement:' + accepted['id'],
                          int(not selected.requires_return or receipt)))
        payments.execute('INSERT INTO contacts VALUES(?,"agreement",?,?,0)', ('acceptance-' + accepted['id'], accepted['id'], cid))
    return cid


class AgreementConnected(Connected):
    def __init__(self, c, db):
        from .config import Config
        # Web serves both ports; the configured base URL determines verification routing.
        adapted = Config({**c.values, 'RP_BASE_URL': c.get('RP_BASE_URL', 'http://127.0.0.1:8000').rstrip('/') + '/agreements'})
        super().__init__(adapted, db)

    def approval(self, case):
        row = self.db.execute('SELECT * FROM agreement_bindings WHERE case_id=?', (case['id'],)).fetchone()
        if not row or not row['charge']:
            raise ValueError('Missing accepted agreement binding')
        terms = json.loads(row['terms'])
        order, offer = validate_terms(terms)
        expected = (row['charge'], order.reference, row['customer'], order.paid_cents,
                    offer.refund_cents, 'usd', 'agreement:' + row['agreement_id'])
        actual = tuple(case[k] for k in ('charge', 'order_ref', 'customer', 'original', 'amount', 'currency', 'policy'))
        if actual != expected:
            raise ValueError('Case differs from accepted terms')
        return order.paid_cents, offer.refund_cents


def send_verification(payments, provider, cid):
    row = payments.execute('SELECT id FROM contacts WHERE case_id=? AND channel="agreement"', (cid,)).fetchone()
    if not row:
        raise ValueError('No bound contact')
    return issue(payments, provider, row['id'], provider.c.get('RP_BASE_URL'))


def record_receipt(payments, cid):
    with payments:
        if not payments.execute('SELECT 1 FROM agreement_bindings WHERE case_id=?', (cid,)).fetchone():
            raise ValueError('No bound case')
        payments.execute('UPDATE agreement_bindings SET return_received=1 WHERE case_id=?', (cid,))
        payments.execute('UPDATE cases SET warehouse=1 WHERE id=?', (cid,))


def readback(c, path):
    """Independent variable-amount Stripe checker; no planner success flags."""
    db = journal(path)
    try:
        rows = db.execute('SELECT b.*,o.id AS operation FROM agreement_bindings b JOIN operations o ON o.case_id=b.case_id').fetchall()
        client = stripe_client(c)
        if client.v1.accounts.retrieve_current().id != c.get('RP_STRIPE_ACCOUNT_ID'):
            raise ValueError('Stripe account mismatch')
        results = []
        for row in rows:
            terms = json.loads(row['terms'])
            order, offer = validate_terms(terms)
            charge = client.v1.charges.retrieve(row['charge'])
            refunds = list(client.v1.refunds.list({'charge': row['charge'], 'limit': 100}).auto_paging_iter())
            matched = [r for r in refunds if r.metadata.get('operation') == row['operation'] and r.metadata.get('case_id') == row['case_id']]
            ok = len(refunds) == len(matched) == 1 and charge.amount == order.paid_cents and charge.currency == 'usd' and charge.livemode is False
            if ok:
                refund = client.v1.refunds.retrieve(matched[0].id)
                ok = refund.amount == offer.refund_cents and refund.currency == 'usd' and refund.charge == row['charge'] and refund.status == 'succeeded'
            results.append({'case_alias': hashlib.sha256(row['case_id'].encode()).hexdigest()[:16],
                            'original_cents': order.paid_cents, 'approved_cents': offer.refund_cents,
                            'refund_count': len(refunds), 'aggregate_cents': sum(r.amount for r in refunds), 'passed': bool(ok)})
        return {'results': results, 'passed': bool(results) and all(r['passed'] for r in results)}
    finally:
        db.close()
