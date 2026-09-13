"""Independent read-only Stripe TEST oracle. Does not import planner or Connected adapter."""
from .auth import stripe_client


def stripe_records(c, charge_id, operation_id, case_id):
    client = stripe_client(c)
    account = client.v1.accounts.retrieve_current()
    if account.id != c.get('RP_STRIPE_ACCOUNT_ID'):
        raise ValueError('Independent oracle account mismatch')
    charge = client.v1.charges.retrieve(charge_id)
    if charge.livemode is not False or charge.amount != 10000 or charge.currency != 'usd':
        raise ValueError('Independent oracle charge mismatch')
    rows = list(client.v1.refunds.list({'charge': charge_id, 'limit': 100}).auto_paging_iter())
    matching = [r for r in rows if r.metadata.to_dict().get('operation') == operation_id and r.metadata.to_dict().get('case_id') == case_id]
    checks = {'charge_test': True, 'original_cents': charge.amount, 'refund_count': len(rows),
              'matching_refund_count': len(matching), 'aggregate_cents': sum(r.amount for r in rows),
              'retrieval_matches': False}
    if len(rows) == 1 and len(matching) == 1:
        r = client.v1.refunds.retrieve(matching[0].id)
        checks['retrieval_matches'] = r.id == rows[0].id and r.charge == charge_id and r.amount == 3000 and r.currency == 'usd' and r.status == 'succeeded'
    checks['passed'] = checks['refund_count'] == 1 and checks['matching_refund_count'] == 1 and checks['aggregate_cents'] == 3000 and checks['retrieval_matches']
    return checks
