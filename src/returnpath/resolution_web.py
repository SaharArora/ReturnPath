"""One server-rendered workspace, session-scoped customer view and protected operator view."""
import html
from contextlib import closing
import json
import secrets

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from . import resolution as r


def register(app, c, db_path, page, auth, csrf):
    path = db_path.parent / 'resolutions.sqlite'
    payment_path = db_path.parent / 'agreement-app.sqlite'

    def connected_allowed():
        return c.get('RP_MODE') == 'connected-test' and c.get('RP_ALLOW_CONNECTED_WRITES') == 'true' and c.get('RP_HOSTED') != 'true'


    def session(request):
        if not request.session.get('customer'):
            request.session['customer'] = secrets.token_urlsafe(32)
        if not request.session.get('csrf'):
            request.session['csrf'] = secrets.token_urlsafe(24)
        return request.session['customer']

    def hidden(request):
        return '<input type="hidden" name="csrf" value="' + request.session['csrf'] + '">'

    def heading(payment_mode="SIMULATED PAYMENTS"):
        live = c.get('RP_RESOLUTION_MODEL', 'stub') == 'live'
        return ('<nav><a href="/playground">Customer workspace</a> · <a href="/resolutions">Operator workspace</a> · <a href="/">Connected cases</a></nav>'
                '<p class="badge">' + payment_mode + ' · ' + ('LIVE MODEL' if live else 'DETERMINISTIC OFFLINE BASELINE') +
                '</p><p>Explore a resolution with one demo merchant. Payments are simulated unless this case is explicitly connected to Stripe TEST.</p>')

    @app.get('/playground')
    def home(request: Request):
        owner = session(request)
        content = heading() + '<h2>Find a resolution that works for you</h2><p>Choose a demo purchase, explain what happened, and review exact terms before accepting.</p>'
        for order in r.catalog(c).orders:
            content += '<article><h3>' + html.escape(order.product) + '</h3><p>Order ' + order.reference + ' · $' + f'{order.paid_cents / 100:.2f}' + '</p><form method="post" action="/playground/start">' + hidden(request) + '<input type="hidden" name="reference" value="' + order.reference + '"><button>Resolve this purchase</button></form></article>'
        with closing(r.connect(path)) as db:
            for row in db.execute('SELECT id,state FROM resolutions WHERE owner=? ORDER BY created DESC LIMIT 20', (r.owner_hash(owner),)):
                content += '<p><a href="/playground/' + row['id'] + '">Continue request</a> · ' + html.escape(row['state']) + '</p>'
        return page(content)

    @app.post('/playground/start')
    async def start(request: Request):
        owner = session(request)
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        with closing(r.connect(path)) as db:
            if db.execute('SELECT count(*) FROM resolutions WHERE owner=?', (r.owner_hash(owner),)).fetchone()[0] >= 10:
                raise HTTPException(429, 'Demo session limit reached')
            try:
                rid = r.start(db, owner, r.catalog(c), str(data.get('reference', '')))
            except ValueError:
                raise HTTPException(400, 'Invalid demo order') from None
        return RedirectResponse('/playground/' + rid, 303)

    def render(db, row, request, operator=False):
        rid = row['id']
        terms = json.loads(row['terms'])
        linked = None
        if payment_path.exists():
            from .agreement_bridge import journal
            with closing(journal(payment_path)) as payments:
                linked = payments.execute('SELECT c.* FROM cases c JOIN agreement_bindings b ON b.case_id=c.id WHERE b.resolution_id=?', (rid,)).fetchone()
        content = heading('STRIPE TEST' if linked else 'SIMULATED PAYMENTS') + '<h2>' + html.escape(terms['order']['product']) + '</h2><p>Status: <strong>' + row['state'] + '</strong> · Round ' + str(row['rounds']) + '/3</p>'
        for entry in db.execute('SELECT * FROM exchanges WHERE resolution=? ORDER BY id', (rid,)):
            data = json.loads(entry['data'])
            content += '<article><h3>' + {'customer': 'You', 'advocate': 'Your advocate', 'merchant': 'Merchant representative'}[entry['role']] + '</h3><p>' + html.escape(data['explanation']) + '</p><small>Round ' + str(entry['round']) + ' · ' + html.escape(data['action']) + '</small></article>'
        offer = db.execute('SELECT * FROM offers WHERE resolution=? ORDER BY rowid DESC LIMIT 1', (rid,)).fetchone()
        if offer:
            chosen = json.loads(offer['terms'])['selected']
            content += '<article><h3>Exact proposed terms</h3><p>' + html.escape(chosen['label']) + '</p><p>Refund: <strong>$' + f'{chosen["refund_cents"] / 100:.2f}' + ' USD</strong></p><p>' + ('Requires warehouse acceptance before payment.' if chosen['requires_return'] else 'Keep the item; no return required.') + '</p>'
            if not operator and row['state'] == 'OFFERED':
                content += '<form method="post" action="/playground/' + rid + '/accept">' + hidden(request) + '<input type="hidden" name="offer" value="' + offer['id'] + '"><button>Accept these exact terms</button></form>'
            content += '</article>'
        if not operator and row['state'] in {'OPEN', 'OFFERED', 'CLARIFY', 'ERROR'} and row['rounds'] < 3:
            content += '<form method="post" action="/playground/' + rid + '/negotiate">' + hidden(request) + '<label>What happened, and what matters to you?<textarea name="request" maxlength="2000" required placeholder="The item arrived damaged. I would prefer to keep it if there is a reasonable partial refund."></textarea></label><button>Ask my advocate</button></form>'
        if row['state'] == 'ERROR':
            content += '<p>The agents could not produce a validated offer. No payment was authorized. You may retry within the remaining round budget.</p>'
        if row['state'] == 'RUNNING':
            content += '<p>Round in progress or interrupted. No automatic restart. Operator inspection required.</p>'
        if operator:
            agreement = db.execute('SELECT * FROM agreements WHERE resolution=?', (rid,)).fetchone()
            if agreement:
                content += '<article><h3>Durable accepted agreement</h3><pre>' + html.escape(agreement['terms']) + '</pre></article>'
                if connected_allowed():
                    content += '<article><h3>Connect this agreement to Stripe TEST</h3><p>Creates a fresh TEST payment for the purchase price and sends a verification link to the configured customer. The worker can refund only the accepted amount after confirmation.</p><form method="post" action="/resolutions/' + rid + '/connect">' + hidden(request) + '<button>Prepare Stripe TEST case / send verification</button></form></article>'
                content += '<form method="post" action="/resolutions/' + rid + '/settle">' + hidden(request) + '<label><input type="checkbox" name="receipt" value="yes">Simulate warehouse acceptance, if required</label><button>Execute / reconcile simulated refund</button></form>'
        elif row['state'] == 'AGREED' and not linked:
            content += '<p>Your agreement is recorded. The demo operator can execute it in the simulated payment ledger.</p>'
        if payment_path.exists():
            from .agreement_bridge import journal
            with closing(journal(payment_path)) as payments:
                linked = payments.execute('SELECT c.* FROM cases c JOIN agreement_bindings b ON b.case_id=c.id WHERE b.resolution_id=?', (rid,)).fetchone()
                if linked:
                    content += '<article><h3>STRIPE TEST execution</h3><p>Approved $' + f"{linked['amount']/100:.2f}" + ' · ' + html.escape(linked['summary']) + '</p><p>Identity must be confirmed through the customer email before payment.</p></article>'
        if linked and operator:
            content += '<p><a href="/agreements/cases/' + linked['id'] + '">Inspect payment evidence / record simulated warehouse acceptance</a></p>'
        return page(content)

    @app.get('/playground/{rid}')
    def detail(request: Request, rid: str):
        owner = session(request)
        with closing(r.connect(path)) as db:
            try:
                row = r.owned(db, rid, owner)
            except ValueError:
                raise HTTPException(404) from None
            return render(db, row, request)

    @app.post('/playground/{rid}/negotiate')
    async def negotiate(request: Request, rid: str):
        owner = session(request)
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        # Sync inference runs outside the event loop so other requests stay usable.
        from starlette.concurrency import run_in_threadpool
        def work():
            with closing(r.connect(path)) as db:
                r.negotiate(db, c, rid, owner, str(data.get('request', '')))
        try:
            await run_in_threadpool(work)
        except Exception:
            return page(heading() + '<p>No new agreement was authorized. Request unavailable, round limit reached, or model validation failed.</p><a href="/playground">Back to requests</a>')
        return RedirectResponse('/playground/' + rid, 303)

    @app.post('/playground/{rid}/accept')
    async def accept(request: Request, rid: str):
        owner = session(request)
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        with closing(r.connect(path)) as db:
            try:
                r.accept(db, rid, owner, str(data.get('offer', '')))
            except ValueError:
                raise HTTPException(409, 'Offer unavailable, superseded, expired or already accepted with different terms') from None
        return RedirectResponse('/playground/' + rid, 303)

    @app.get('/resolutions')
    def operations(request: Request):
        auth(request)
        content = heading() + '<h2>Resolution queue</h2><p>Inspect both parties, accepted terms and simulated execution.</p>'
        with closing(r.connect(path)) as db:
            for row in db.execute('SELECT * FROM resolutions ORDER BY created DESC LIMIT 100'):
                terms = json.loads(row['terms'])
                content += '<article><a href="/resolutions/' + row['id'] + '">' + html.escape(terms['order']['product']) + '</a><p>' + row['state'] + '</p></article>'
        return page(content)

    @app.get('/resolutions/{rid}')
    def operation(request: Request, rid: str):
        auth(request)
        with closing(r.connect(path)) as db:
            row = db.execute('SELECT * FROM resolutions WHERE id=?', (rid,)).fetchone()
            if not row:
                raise HTTPException(404)
            return render(db, row, request, operator=True)

    @app.post('/resolutions/{rid}/settle')
    async def settle(request: Request, rid: str):
        auth(request)
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        with closing(r.connect(path)) as db:
            try:
                r.settle_simulated(db, rid, path.parent / 'resolution-provider.sqlite', data.get('receipt') == 'yes')
            except ValueError:
                raise HTTPException(409, 'Accepted agreement and required warehouse evidence are necessary') from None
        return RedirectResponse('/resolutions/' + rid, 303)

    @app.post('/resolutions/{rid}/connect')
    async def connect_agreement(request: Request, rid: str):
        auth(request)
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        if not connected_allowed():
            raise HTTPException(403, 'Connected TEST writes are not enabled')
        from .agreement_bridge import journal, prepare, AgreementConnected, send_verification
        from starlette.concurrency import run_in_threadpool
        def work():
            with closing(r.connect(path)) as resolutions, closing(journal(payment_path)) as payments:
                cid = prepare(c, resolutions, payments, rid)
                provider = AgreementConnected(c, payments)
                send_verification(payments, provider, cid)
        try:
            await run_in_threadpool(work)
        except Exception as exc:
            print('Agreement preparation pending: ' + type(exc).__name__, flush=True)
            return page('<p>Preparation or verification is pending. No automatic replacement payment will be created. Inspect the agreement execution journal.</p>')
        return RedirectResponse('/resolutions/' + rid, 303)

    @app.get('/agreements/verify/{token}')
    def agreement_verify_form(request: Request, token: str):
        from .agreement_bridge import journal
        from .identity import challenge
        with closing(journal(payment_path)) as payments:
            row = challenge(payments, token)
            if not row:
                return page('<p>Request unavailable or expired.</p>')
            case = payments.execute('SELECT amount FROM cases WHERE id=?', (row['case_id'],)).fetchone()
        request.session['csrf'] = secrets.token_urlsafe(24)
        return page('<h2>Confirm accepted refund</h2><p>Order ' + html.escape(row['order_ref']) + ' · approved $' + f"{case['amount']/100:.2f}" + ' USD in Stripe TEST. Confirm control of the trusted customer mailbox for this request.</p><form method="post">' + hidden(request) + '<button>Confirm this request</button></form>')

    @app.post('/agreements/verify/{token}')
    async def agreement_verify(request: Request, token: str):
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        from .agreement_bridge import journal
        from .identity import confirm
        with closing(journal(payment_path)) as payments:
            confirm(payments, token)
        return page('<p>Request processed. The worker will check the accepted terms and provider records.</p>')

    @app.get('/agreements/cases/{cid}')
    def agreement_case(request: Request, cid: str):
        auth(request)
        from .agreement_bridge import journal
        with closing(journal(payment_path)) as payments:
            row = payments.execute('SELECT * FROM cases WHERE id=?', (cid,)).fetchone()
            if not row:
                raise HTTPException(404)
            content = '<h2>Agreement execution · STRIPE TEST</h2><p>Order ' + html.escape(row['order_ref']) + ' · approved $' + f"{row['amount']/100:.2f}" + '</p><p>' + html.escape(row['summary']) + '</p>'
            if not row['warehouse']:
                content += '<form method="post">' + hidden(request) + '<button>Record simulated warehouse acceptance</button></form>'
            for entry in payments.execute('SELECT kind,data FROM audit WHERE case_id=? ORDER BY id DESC LIMIT 30', (cid,)):
                content += '<pre>' + html.escape(str(dict(entry))) + '</pre>'
        return page(content)

    @app.post('/agreements/cases/{cid}')
    async def agreement_receipt(request: Request, cid: str):
        auth(request)
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        if not connected_allowed():
            raise HTTPException(403)
        from .agreement_bridge import journal, record_receipt
        with closing(journal(payment_path)) as payments:
            record_receipt(payments, cid)
        return RedirectResponse('/agreements/cases/' + cid, 303)
