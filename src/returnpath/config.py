"""Explicit config parsing; never source shell code or expose secret values."""
import os
import secrets
import tempfile
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_CONFIG = "~/.config/returnpath/returnpath.env"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send"]


def atomic_private(path, content):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            os.fchmod(f.fileno(), 0o600)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Config:
    def __init__(self, environ=None):
        env = dict(os.environ if environ is None else environ)
        self.path = Path(env.get("RP_ENV_FILE", DEFAULT_CONFIG)).expanduser()
        values = dotenv_values(self.path, interpolate=False) if self.path.is_file() else {}
        self.values = {**{k: v or "" for k, v in values.items()}, **env}
        if self.get("RP_MODE", "local") not in {"local", "connected-test"}:
            raise ValueError("RP_MODE must be local or connected-test")

    def get(self, key, default=""):
        return self.values.get(key, default)

    def path_value(self, key, default):
        return Path(self.get(key, default)).expanduser()

    def require(self, *keys):
        missing = [k for k in keys if not self.get(k)]
        if missing:
            raise ValueError("Missing configuration: " + ", ".join(missing))

    def writes(self):
        if self.get("RP_MODE", "local") != "connected-test" or self.get("RP_ALLOW_CONNECTED_WRITES") != "true":
            raise ValueError("Connected writes require connected-test mode and explicit write enablement")
        self.require("RP_SUPPORT_EMAIL", "RP_CUSTOMER_EMAIL", "RP_STRIPE_ACCOUNT_ID", "RP_SLACK_CHANNEL_ID")
        if self.get("RP_SUPPORT_EMAIL") == self.get("RP_CUSTOMER_EMAIL"):
            raise ValueError("Use distinct controlled support/customer mailboxes")
        if self.get("RP_MAX_REFUND_CENTS", "3000") != "3000":
            raise ValueError("Baseline refund limit must be 3000 cents")


def init_config(c):
    import getpass

    from argon2 import PasswordHasher
    c.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    c.path.parent.chmod(0o700)
    template = Path(__file__).resolve().parents[2] / ".env.example"
    content = c.path.read_text() if c.path.exists() else template.read_text()
    values = dotenv_values(stream=__import__("io").StringIO(content), interpolate=False)
    updates = {}
    if not values.get("RP_OPERATOR_SESSION_SECRET"):
        updates["RP_OPERATOR_SESSION_SECRET"] = secrets.token_urlsafe(48)
    if not values.get("RP_OPERATOR_PASSWORD_HASH"):
        password = getpass.getpass("Choose operator password (12+ characters): ")
        if len(password) < 12 or password != getpass.getpass("Confirm password: "):
            raise ValueError("Password too short or confirmation mismatch; config unchanged")
        updates["RP_OPERATOR_PASSWORD_HASH"] = PasswordHasher().hash(password)
    lines = [line for line in content.splitlines() if line.split("=", 1)[0] not in updates]
    lines.extend(k + "=" + v for k, v in updates.items())
    atomic_private(c.path, "\n".join(lines) + "\n")
    print("Private configuration ready; provider values preserved. Edit locally; never paste secrets into chat.")
