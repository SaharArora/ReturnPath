"""Local explicit OAuth consent and read-only per-service diagnostics."""
import json

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import SCOPES, atomic_private


def gmail(c, consent=False):
    c.require("RP_SUPPORT_EMAIL")
    token = c.path_value("RP_GMAIL_TOKEN_PATH", "~/.config/returnpath/gmail-token.json")
    if consent:
        client = c.path_value("RP_GMAIL_CLIENT_PATH", "~/.config/returnpath/gmail-client.json")
        if not client.is_file():
            raise ValueError("Gmail Desktop OAuth client missing; follow docs/AUTHORIZATION.md")
        flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES, autogenerate_code_verifier=True)
        credentials = flow.run_local_server(host="127.0.0.1", port=0, open_browser=True,
            authorization_prompt_message="Complete Gmail consent in your browser.",
            success_message="Consent received. You may close this tab.", timeout_seconds=180)
    else:
        if not token.is_file():
            raise ValueError("Gmail token missing; run make auth-gmail locally")
        credentials = Credentials.from_authorized_user_file(str(token), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
    if not credentials.valid or not credentials.has_scopes(SCOPES):
        raise ValueError("Gmail grant invalid or missing scopes; reauthorize locally")
    api = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    profile = api.users().getProfile(userId="me").execute(num_retries=0)
    if profile["emailAddress"].lower() != c.get("RP_SUPPORT_EMAIL").lower():
        raise ValueError("Authorized Gmail mailbox does not match RP_SUPPORT_EMAIL")
    atomic_private(token, credentials.to_json())
    return api


def slack_read(c, method, **params):
    c.require("SLACK_BOT_TOKEN", "RP_SLACK_CHANNEL_ID")
    if not c.get("SLACK_BOT_TOKEN").startswith("xoxb-"):
        raise ValueError("Slack requires an installed bot token")
    with httpx.Client(timeout=10) as client:
        r = client.get("https://slack.com/api/" + method,
            headers={"Authorization": "Bearer " + c.get("SLACK_BOT_TOKEN")}, params=params)
        r.raise_for_status()
        data = r.json()
    if not data.get("ok"):
        raise ValueError("Slack read rejected; inspect token scopes, installation and channel membership")
    return data


def stripe_client(c):
    import stripe
    c.require("STRIPE_SECRET_KEY")
    if not c.get("STRIPE_SECRET_KEY").startswith(("sk_test_", "rk_test_")):
        raise ValueError("Only Stripe TEST keys are supported")
    return stripe.StripeClient(c.get("STRIPE_SECRET_KEY"), max_network_retries=0,
        http_client=stripe.HTTPXClient(timeout=10))


def doctor(c, service):
    try:
        if service == "gmail":
            api = gmail(c)
            api.users().messages().list(userId="me", q=c.get("RP_GMAIL_QUERY", 'subject:"[ReturnPath Demo]" -in:sent'), maxResults=1).execute(num_retries=0)
        elif service == "slack":
            slack_read(c, "auth.test")
            channel = slack_read(c, "conversations.info", channel=c.get("RP_SLACK_CHANNEL_ID"))["channel"]
            if not channel.get("is_private") or not channel.get("is_member"):
                raise ValueError("Slack bot must belong to the configured private channel")
        elif service == "stripe":
            account = stripe_client(c).v1.accounts.retrieve_current()
            if c.get("RP_STRIPE_ACCOUNT_ID") and account.id != c.get("RP_STRIPE_ACCOUNT_ID"):
                raise ValueError("Stripe account mismatch")
            return {"service": service, "status": "AUTHENTICATED", "actions": "ACTION_UNVERIFIED", "account_id": account.id}
        elif service == "model":
            c.require("OPENAI_API_KEY", "RP_MODEL")
            return {"service": service, "status": "CONFIGURED", "actions": "ACTION_UNVERIFIED", "note": "No inference performed"}
        else:
            raise ValueError("Unknown service")
        return {"service": service, "status": "AUTHENTICATED", "actions": "ACTION_UNVERIFIED"}
    except Exception as e:
        # Provider exception messages can contain request URLs or raw response bodies.
        detail = str(e) if type(e) is ValueError else type(e).__name__ + ": authorization/read failed; check local provider setup"
        return {"service": service, "status": "BLOCKED", "reason": detail}


def print_doctors(c, services):
    results = [doctor(c, s) for s in services]
    print(json.dumps(results, indent=2))
    return int(any(r["status"] == "BLOCKED" for r in results))
