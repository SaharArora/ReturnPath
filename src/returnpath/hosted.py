"""Hosted playground only. Never loads Mac config or exposes connected execution routes."""
import os

from argon2 import PasswordHasher

from .config import Config
from .web import create_app


def build(environ=None):
    env = dict(os.environ if environ is None else environ)
    if any(env.get(key) for key in ('STRIPE_SECRET_KEY', 'SLACK_BOT_TOKEN', 'RP_GMAIL_TOKEN_PATH', 'RP_GMAIL_CLIENT_PATH')):
        raise ValueError('Hosted playground rejects financial/messaging credentials')
    if env.get('RP_ALLOW_CONNECTED_WRITES', 'false') != 'false':
        raise ValueError('Hosted playground cannot enable connected writes')
    password = env.pop('RP_OPERATOR_PASSWORD', '')
    if len(password) < 12:
        raise ValueError('Set a separate hosted operator password of at least 12 characters')
    host = env.get('RP_PUBLIC_HOST') or env.get('RENDER_EXTERNAL_HOSTNAME')
    if not host or '/' in host or ':' in host or '*' in host:
        raise ValueError('An exact public hostname is required')
    env.update(RP_ENV_FILE='/dev/null', RP_HOSTED='true', RP_PUBLIC_HOST=host,
               RP_MODE='connected-test', RP_ALLOW_CONNECTED_WRITES='false',
               RP_OPERATOR_PASSWORD_HASH=PasswordHasher().hash(password),
               RP_STATE_DIR=env.get('RP_STATE_DIR', '/var/data/returnpath'))
    c = Config(env)
    c.require('RP_OPERATOR_SESSION_SECRET')
    if c.get('RP_RESOLUTION_MODEL', 'stub') == 'live':
        c.require('OPENAI_API_KEY', 'RP_MODEL')
    app = create_app(c)
    app.router.routes[:] = [route for route in app.routes if
        route.path == '/login' or route.path.startswith(('/playground', '/resolutions'))]

    @app.get('/health')
    def health():
        return {'status': 'ok', 'payments': 'simulated'}

    @app.get('/')
    def home():
        from fastapi.responses import RedirectResponse
        return RedirectResponse('/playground', 303)

    return app
