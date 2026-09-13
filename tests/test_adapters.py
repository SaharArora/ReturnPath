from types import SimpleNamespace as Obj
import pytest
from returnpath.connected import Connected
from returnpath.config import Config


def test_F16_stripe_later_page(world):
    db, _ = world
    adapter = object.__new__(Connected)
    adapter.db = db
    refund = Obj(id='re_later', charge='ch', amount=3000, currency='usd', metadata={}, status='pending')
    class Pages:
        def auto_paging_iter(self):
            yield refund
    class Charges:
        def retrieve(self, charge):
            return Obj(id=charge, amount=10000, currency='usd', livemode=False, paid=True,
                       captured=True, disputed=False, payment_method_details=Obj(type='card'))
    class Refunds:
        def list(self, params):
            assert params == {'charge': 'ch', 'limit': 100}
            return Pages()
    adapter.stripe = Obj(v1=Obj(charges=Charges(), refunds=Refunds()))
    _, rows = adapter.observe('ch')
    assert len(rows) == 1 and rows[0]['id'] == 're_later'


def test_F28_write_gate():
    with pytest.raises(ValueError):
        Config({'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'local', 'RP_ALLOW_CONNECTED_WRITES': 'true'}).writes()


def test_F28_live_key_rejected():
    from returnpath.auth import stripe_client
    with pytest.raises(ValueError):
        stripe_client(Config({'RP_ENV_FILE': '/dev/null', 'STRIPE_SECRET_KEY': 'sk_live_synthetic'}))


def test_gmail_complete_pagination():
    adapter = object.__new__(Connected)
    seen = []
    class Messages:
        def list(self, **params):
            seen.append(params['pageToken'])
            data = {'messages': [{'id': 'first'}], 'nextPageToken': 'page2'} if not params['pageToken'] else {'messages': [{'id': 'second'}]}
            return Obj(execute=lambda **kwargs: data)
    adapter.gmail = Obj(users=lambda: Obj(messages=lambda: Messages()))
    assert [m['id'] for m in adapter.list_messages('scoped')] == ['first', 'second']
    assert seen == [None, 'page2']


@pytest.mark.parametrize('broken_page', [False, True])
def test_F11_F16_actual_sdk_pagination(world, broken_page):
    import httpx
    import stripe
    db, _ = world
    seen = []
    def handle(request):
        seen.append(str(request.url))
        if '/charges/' in request.url.path:
            return httpx.Response(200, json={'object': 'charge', 'id': 'ch', 'amount': 10000,
                'currency': 'usd', 'livemode': False, 'paid': True, 'captured': True,
                'disputed': False, 'payment_method_details': {'type': 'card'}})
        if request.url.params.get('starting_after'):
            if broken_page:
                return httpx.Response(503, json={'error': {'message': 'synthetic outage', 'type': 'api_error'}})
            return httpx.Response(200, json={'object': 'list', 'url': '/v1/refunds', 'has_more': False,
                'data': [{'object': 'refund', 'id': 're_matching', 'charge': 'ch', 'amount': 3000,
                          'currency': 'usd', 'metadata': {'operation': 'op', 'case_id': 'ret'}, 'status': 'succeeded'}]})
        return httpx.Response(200, json={'object': 'list', 'url': '/v1/refunds', 'has_more': True,
            'data': [{'object': 'refund', 'id': 're_first', 'charge': 'ch', 'amount': 100,
                      'currency': 'usd', 'metadata': {}, 'status': 'succeeded'}]})
    transport = stripe.HTTPXClient(timeout=10, allow_sync_methods=True)
    transport._client.close()
    transport._client = httpx.Client(transport=httpx.MockTransport(handle))
    adapter = object.__new__(Connected)
    adapter.db = db
    adapter.stripe = stripe.StripeClient('sk_test_synthetic', max_network_retries=0, http_client=transport)
    try:
        if broken_page:
            with pytest.raises(stripe.APIError):
                adapter.observe('ch')
        else:
            _, rows = adapter.observe('ch')
            assert [r['id'] for r in rows] == ['re_first', 're_matching']
        assert any('starting_after=re_first' in url for url in seen)
    finally:
        transport._client.close()
