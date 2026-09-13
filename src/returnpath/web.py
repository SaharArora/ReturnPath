"""Loopback-only protected operator UI; explicit scoped verification confirmation."""
import html
import secrets
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from .runtime import paths
from .storage import connect
from .identity import challenge, confirm


def create_app(c):
    c.require("RP_OPERATOR_SESSION_SECRET", "RP_OPERATOR_PASSWORD_HASH")
    if len(c.get("RP_OPERATOR_SESSION_SECRET")) < 32:
        raise ValueError("Operator session secret too short; run make init-config")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SessionMiddleware, secret_key=c.get("RP_OPERATOR_SESSION_SECRET"),
                       same_site="strict", max_age=3600)
    db_path, _ = paths(c)
    attempts = {}

    @app.middleware("http")
    async def security(request, call_next):
        if request.headers.get("host", "").split(":")[0] not in {"localhost", "127.0.0.1", "testserver"}:
            return HTMLResponse("Invalid host", status_code=400)
        response = await call_next(request)
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'"
        return response

    def page(content):
        return HTMLResponse("<!doctype html><html><head><title>ReturnPath</title><style>body{font:16px system-ui;max-width:1000px;margin:3em auto;padding:1em;background:#f5f5f0;color:#18312c}article{background:white;padding:1.5em;margin:1em 0;border:1px solid #ccc}pre{white-space:pre-wrap}a{color:#175d51}input,button{padding:.7em;margin:.5em}</style></head><body><h1>ReturnPath</h1>" + content + "</body></html>")

    def auth(request):
        if not request.session.get("operator"):
            raise HTTPException(401, "Operator login required")

    def csrf(request, supplied):
        expected = request.session.get("csrf")
        if not expected or not secrets.compare_digest(expected, supplied):
            raise HTTPException(403, "Invalid confirmation")

    @app.get("/warehouse/{case_id}")
    def warehouse(request: Request, case_id: str):
        if not secrets.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + c.get('RP_OPERATOR_SESSION_SECRET')):
            raise HTTPException(401)
        from .warehouse import observe
        return observe(db_path.parent / 'warehouse.sqlite', case_id)

    @app.get("/login")
    def login_form(request: Request):
        token = secrets.token_urlsafe(24)
        request.session["csrf"] = token
        return page('<form method="post"><input type="hidden" name="csrf" value="' + token + '"><label>Operator password <input name="password" type="password" required></label><button>Log in</button></form>')

    @app.post("/login")
    async def login(request: Request):
        data = await request.form()
        csrf(request, str(data.get("csrf", "")))
        host = request.client.host
        now = time.time()
        attempts[host] = [t for t in attempts.get(host, []) if now - t < 60]
        if len(attempts[host]) >= 5:
            raise HTTPException(429, "Try again later")
        attempts[host].append(now)
        try:
            PasswordHasher().verify(c.get("RP_OPERATOR_PASSWORD_HASH"), str(data.get("password", "")))
        except VerificationError:
            raise HTTPException(401, "Invalid login") from None
        request.session.clear()
        request.session.update(operator=True, csrf=secrets.token_urlsafe(24))
        return RedirectResponse("/", status_code=303)

    @app.get("/")
    def index(request: Request):
        auth(request)
        db = connect(db_path)
        try:
            content = '<p>' + html.escape(c.get("RP_MODE", "local")) + ' · SIMULATED RETURN EVIDENCE · no automatic restart</p>'
            for row in db.execute("SELECT * FROM cases"):
                content += '<article><a href="/cases/' + row['id'] + '">Order ' + row['order_ref'] + '</a><p>Original $100 · Approved $30</p><p>' + html.escape(row['summary']) + '</p></article>'
            for row in db.execute("SELECT * FROM heartbeats"):
                content += '<p>' + html.escape(row['component']) + ' heartbeat age: ' + str(round(time.time() - row['at'], 1)) + 's</p>'
            return page(content)
        finally:
            db.close()

    @app.get("/cases/{case_id}")
    def detail(request: Request, case_id: str):
        auth(request)
        db = connect(db_path)
        try:
            row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
            if not row:
                raise HTTPException(404)
            content = '<p><a href="/">Cases</a></p><h2>Order ' + row['order_ref'] + '</h2><p>Original $100 · Approved $30 · SIMULATED WAREHOUSE</p>'
            for title, query in [
                ('Trusted case', 'SELECT * FROM cases WHERE id=?'),
                ('Contacts (verification is contact scoped)', 'SELECT * FROM contacts WHERE case_id=?'),
                ('Durable operation', 'SELECT * FROM operations WHERE case_id=?'),
                ('Notification submission', 'SELECT id,state,provider_id FROM notifications WHERE case_id=?'),
                ('Observed trace', 'SELECT at,kind,data FROM audit WHERE case_id=? ORDER BY id DESC LIMIT 100')]:
                content += '<article><h3>' + title + '</h3>'
                for item in db.execute(query, (case_id,)):
                    content += '<pre>' + html.escape(str(dict(item))) + '</pre>'
                content += '</article>'
            return page(content)
        finally:
            db.close()

    @app.get("/verify/{token}")
    def verify_get(request: Request, token: str):
        db = connect(db_path)
        try:
            row = challenge(db, token)
            if not row:
                return page('<p>Request unavailable or expired.</p>')
            csrf_token = secrets.token_urlsafe(24)
            request.session['csrf'] = csrf_token
            return page('<h2>Confirm order ' + html.escape(row['order_ref']) + ' status request</h2><p>This verifies this contact only. The approved refund amount cannot change.</p><form method="post"><input type="hidden" name="csrf" value="' + csrf_token + '"><button>Confirm request</button></form>')
        finally:
            db.close()

    @app.post("/verify/{token}")
    async def verify_post(request: Request, token: str):
        data = await request.form()
        csrf(request, str(data.get('csrf', '')))
        db = connect(db_path)
        try:
            confirm(db, token)
            return page('<p>Request processed. You may close this page.</p>')
        finally:
            db.close()

    return app
