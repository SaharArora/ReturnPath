"""Public loopback setup instructions only. No credentials, case data or mutations."""
import html
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parents[2]


def page(title, body):
    return HTMLResponse("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>" + title + " — ReturnPath</title><style>body{font:17px/1.6 system-ui;background:#f4f6f2;color:#18342e;max-width:880px;margin:48px auto;padding:24px}nav a{margin-right:24px;color:#185d4d}article{background:white;border:1px solid #d2ddd5;border-radius:12px;padding:28px;margin-top:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2ed;padding:20px}code{font-size:15px}li{margin:16px 0}h1{line-height:1.2}a{color:#17644e}</style></head><body><nav><strong>ReturnPath</strong> · <a href='/login'>Setup</a><a href='/credentials'>Credentials checklist</a><a href='/authorization'>Detailed instructions</a></nav><article><h1>" + title + "</h1>" + body + "</article></body></html>")


def create_setup_app():
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def secure(request, call_next):
        if request.headers.get('host', '').split(':')[0] not in {'127.0.0.1', 'localhost', 'testserver'}:
            return HTMLResponse('Invalid host', status_code=400)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"
        return response

    @app.get('/')
    @app.get('/login')
    def setup():
        return page('Finish local setup', "<p>The preview server is running. Your operator login has not been configured yet, so the dashboard is not available.</p><p>In your Mac Terminal, run:</p><pre><code>cd ~/testingxd\nmake init-config</code></pre><p>Choose your operator password in Terminal. It will not echo as you type. Existing provider settings are preserved.</p><p>Then tell the assistant setup is done so it can restart this preview as the protected dashboard. No provider accounts are needed to use the local simulation.</p><p><a href='/credentials'>Open the single credentials checklist →</a></p><p><strong>Status:</strong> setup instructions only. No refunds, emails or Slack messages run from this page.</p>")

    @app.get('/credentials')
    def credentials():
        return page('Single credentials checklist', "<p>Keep credentials in <code>~/.config/returnpath/returnpath.env</code> on this Mac. Never paste them into chat.</p><ol><li><strong>Local login:</strong> run <code>make init-config</code> in <code>~/testingxd</code> and choose your operator password privately.</li><li><strong>Gmail:</strong> use a dedicated support mailbox and separate controlled customer mailbox. Enable Gmail API, add your support test user, and save the Desktop OAuth client as <code>~/.config/returnpath/gmail-client.json</code>. Set <code>RP_SUPPORT_EMAIL</code> and <code>RP_CUSTOMER_EMAIL</code>; run <code>make auth-gmail</code> and complete browser consent yourself.</li><li><strong>Slack:</strong> install the supplied bot manifest and invite the bot to a private demo channel. Save <code>SLACK_BOT_TOKEN</code> and <code>RP_SLACK_CHANNEL_ID</code> locally.</li><li><strong>Stripe TEST:</strong> create your Stripe account yourself. Use its test environment and save <code>STRIPE_SECRET_KEY</code>. Run the Stripe doctor, confirm its account ID, and save it as <code>RP_STRIPE_ACCOUNT_ID</code>.</li><li><strong>Model:</strong> save a separately authorized <code>OPENAI_API_KEY</code> and available <code>RP_MODEL</code> locally.</li><li><strong>Check each service:</strong><pre>make doctor SERVICE=gmail\nmake doctor SERVICE=slack\nmake doctor SERVICE=stripe\nmake doctor SERVICE=model</pre>These checks do not send mail, post Slack messages or issue refunds. Keep connected writes disabled until you are ready for the controlled test.</li></ol><p><a href='/authorization'>Open detailed account and consent instructions →</a></p>")

    @app.get('/authorization')
    def authorization():
        return page('Account and consent instructions', '<pre>' + html.escape((ROOT / 'docs/AUTHORIZATION.md').read_text()) + '</pre>')

    return app
