"""Actual provider APIs; never fall back to simulators. Contract evidence remains opt-in."""
import base64
import html
import re
import email
from email.message import EmailMessage
from email.policy import default
import hashlib
import json
import time
import uuid
import httpx
from .auth import gmail, slack_read, stripe_client


def slack_equivalent(actual, expected):
    # Slack renders bare URLs as <URL>; only normalize that documented markup.
    def canonical(text):
        return re.sub(r'<(https?://[^<>|]+)>', r'\1', html.unescape(text))
    return canonical(actual) == canonical(expected)


class Connected:
    def __init__(self, c, db):
        self.c, self.db = c, db
        c.writes()
        self.stripe = stripe_client(c)
        account = self.stripe.v1.accounts.retrieve_current()
        if account.id != c.get("RP_STRIPE_ACCOUNT_ID"):
            raise ValueError("Stripe account mismatch")
        self.gmail = gmail(c)
        channel = slack_read(c, "conversations.info", channel=c.get("RP_SLACK_CHANNEL_ID"))["channel"]
        if not channel.get("is_private") or not channel.get("is_member"):
            raise ValueError("Slack requires membership in configured private channel")
        db.execute("CREATE TABLE IF NOT EXISTS slack_outbox (id TEXT PRIMARY KEY, ts TEXT, attempted REAL)")
        db.commit()

    def observe(self, charge):
        if not self.db.execute("SELECT 1 FROM cases WHERE charge=?", (charge,)).fetchone():
            raise ValueError("Unseeded charge")
        ch = self.stripe.v1.charges.retrieve(charge)
        if ch.livemode is not False:
            raise ValueError("Live object rejected")
        rows = []
        for refund in self.stripe.v1.refunds.list({"charge": charge, "limit": 100}).auto_paging_iter():
            rows.append(self.normalize(refund))
        stored = self.db.execute("SELECT provider_id FROM operations o JOIN cases c ON c.id=o.case_id WHERE c.charge=?", (charge,)).fetchone()
        if stored and stored[0]:
            retrieved = self.stripe.v1.refunds.retrieve(stored[0])
            if self.normalize(retrieved) not in rows:
                raise ValueError("Stored refund differs from complete listing")
        return ({"id": ch.id, "amount": ch.amount, "currency": ch.currency, "livemode": ch.livemode,
                 "paid": ch.paid, "captured": ch.captured, "disputed": ch.disputed,
                 "type": ch.payment_method_details.type}, rows)

    @staticmethod
    def normalize(r):
        metadata = r.metadata if isinstance(r.metadata, dict) else r.metadata.to_dict()
        return {"id": r.id, "charge": r.charge, "amount": r.amount, "currency": r.currency,
                "operation": metadata.get("operation"), "case_id": metadata.get("case_id"), "status": r.status}

    def refund(self, op, params):
        self.c.writes()
        trusted = self.db.execute("SELECT * FROM cases WHERE id=?", (op["case_id"],)).fetchone()
        amount = self.approval(dict(trusted))[1] if trusted and hasattr(self, "approval") else 3000
        if not trusted or params != {"charge": trusted["charge"], "amount": amount, "currency": "usd", "policy": trusted["policy"]}:
            raise ValueError("Refund parameters not approved")
        if not self.db.execute("SELECT 1 FROM operations WHERE id=? AND first_attempt IS NOT NULL AND attempts<=3", (op["id"],)).fetchone():
            raise ValueError("Missing durable attempt")
        from .limits import reserve
        reserve(self.db, 'refund_posts', 3)
        import stripe
        try:
            refund = self.stripe.v1.refunds.create({"charge": params["charge"], "amount": amount,
                         "metadata": {"operation": op["id"], "case_id": op["case_id"]}}, {"idempotency_key": op["idem"]})
        except (stripe.AuthenticationError, stripe.PermissionError, stripe.InvalidRequestError) as exc:
            raise ValueError('Stripe definite request/configuration error: ' + type(exc).__name__) from None
        if refund.charge != trusted["charge"] or refund.amount != amount or refund.currency != "usd":
            raise ValueError("Refund response conflict")
        return {"id": refund.id}

    @staticmethod
    def message_id(semantic):
        return hashlib.sha256(semantic.encode()).hexdigest() + "@returnpath.invalid"

    def send(self, semantic, recipient, body):
        self.c.writes()
        if recipient != self.c.get("RP_CUSTOMER_EMAIL"):
            raise ValueError("Recipient is not allowlisted")
        from .limits import reserve
        reserve(self.db, 'mail_posts', 20)
        msg = EmailMessage()
        msg["To"] = recipient
        msg["From"] = self.c.get("RP_SUPPORT_EMAIL")
        msg["Subject"] = "[ReturnPath Demo] Request update"
        msg["Message-ID"] = "<" + self.message_id(semantic) + ">"
        msg.set_content(body)
        result = self.gmail.users().messages().send(userId="me", body={"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}).execute(num_retries=0)
        return result["id"]

    def list_messages(self, query):
        page = None
        seen = set()
        while True:
            data = self.gmail.users().messages().list(userId="me", q=query, maxResults=100, pageToken=page).execute(num_retries=0)
            yield from data.get("messages", [])
            page = data.get("nextPageToken")
            if not page:
                break
            if page in seen:
                raise ValueError("Repeated Gmail page token")
            seen.add(page)

    def read_message(self, mid):
        result = self.gmail.users().messages().get(userId="me", id=mid, format="raw").execute(num_retries=0)
        raw = base64.urlsafe_b64decode(result["raw"])
        if len(raw) > 64000:
            raise ValueError("Oversized email")
        return email.message_from_bytes(raw, policy=default), result

    def sent(self, semantic, recipient, body):
        found = []
        mid = self.message_id(semantic)
        for item in self.list_messages("in:sent rfc822msgid:" + mid):
            msg, data = self.read_message(item["id"])
            part = msg.get_body(preferencelist=("plain",))
            if ("SENT" in data.get("labelIds", []) and msg["Message-ID"] == "<" + mid + ">"
                and email.utils.parseaddr(msg["To"])[1] == recipient and part
                and part.get_content().strip() == body.strip()):
                found.append({"id": item["id"]})
        return found

    def intake(self):
        from .identity import ingest, issue
        query = self.c.get("RP_GMAIL_QUERY", 'subject:"[ReturnPath Demo]" -in:sent')
        for item in self.list_messages(query):
            existing = self.db.execute("SELECT * FROM contacts WHERE channel='gmail' AND event=?", (item["id"],)).fetchone()
            if existing and existing["verified"]:
                continue
            if existing and existing['case_id']:
                issue(self.db, self, existing['id'], self.c.get('RP_BASE_URL', 'http://127.0.0.1:8000'))
                continue
            if existing and self.db.execute("SELECT 1 FROM sqlite_master WHERE name='model_attempts'").fetchone():
                budget = self.db.execute('SELECT count,next_at FROM model_attempts WHERE contact=?', (existing['id'],)).fetchone()
                if budget and (budget['count'] >= 3 or time.time() < budget['next_at']):
                    continue
            msg, data = self.read_message(item["id"])
            sender = email.utils.parseaddr(msg["From"])[1]
            if 'SENT' in data.get('labelIds', []) or sender != self.c.get("RP_CUSTOMER_EMAIL"):
                continue
            part = msg.get_body(preferencelist=("plain",))
            if not part:
                continue
            contact = ingest(self.db, self.c, item["id"], part.get_content())
            bound = self.db.execute('SELECT case_id FROM contacts WHERE id=?', (contact,)).fetchone()
            if bound and bound[0]:
                issue(self.db, self, contact, self.c.get("RP_BASE_URL", "http://127.0.0.1:8000"))
            else:
                self.clarify(contact)

    def clarify(self, contact):
        self.db.execute("CREATE TABLE IF NOT EXISTS clarifications (contact TEXT PRIMARY KEY, state TEXT, provider_id TEXT)")
        self.db.commit()
        if self.db.execute('SELECT 1 FROM clarifications WHERE contact=?', (contact,)).fetchone():
            return  # Ambiguous clarification send is never blindly repeated.
        latest = self.db.execute("SELECT data FROM audit WHERE kind='INTERPRETATION' ORDER BY id DESC LIMIT 100").fetchall()
        if not any(json.loads(r[0]).get('contact') == contact and json.loads(r[0]).get('clarification') for r in latest):
            return
        with self.db:
            self.db.execute("INSERT INTO clarifications VALUES(?,'ATTEMPT_STARTED',NULL)", (contact,))
        try:
            mid = self.send('clarify:' + contact, self.c.get('RP_CUSTOMER_EMAIL'), 'What is your order reference?')
            with self.db:
                self.db.execute("UPDATE clarifications SET state='SUBMITTED',provider_id=? WHERE contact=?", (mid, contact))
        except Exception:
            with self.db:
                self.db.execute("UPDATE clarifications SET state='SEND_UNKNOWN' WHERE contact=?", (contact,))

    def slack(self, case, data):
        self.c.writes()
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO slack_outbox(id) VALUES(?)", (case,))
        row = self.db.execute("SELECT * FROM slack_outbox WHERE id=?", (case,)).fetchone()
        # Lost initial post is left uncertain. Never blindly create another message.
        if row["attempted"] and not row["ts"]:
            raise ValueError("Slack initial post uncertain; inspect private channel")
        text = "ReturnPath TEST | " + case + "\n" + json.dumps(data, sort_keys=True)
        text += "\n" + self.c.get("RP_BASE_URL", "http://127.0.0.1:8000") + "/cases/" + case
        self.db.execute('CREATE TABLE IF NOT EXISTS slack_content (id TEXT PRIMARY KEY, hash TEXT)')
        self.db.commit()
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        prior = self.db.execute('SELECT hash FROM slack_content WHERE id=?', (case,)).fetchone()
        if row['ts'] and prior and prior[0] == content_hash:
            return
        payload = {"channel": self.c.get("RP_SLACK_CHANNEL_ID"), "text": text}
        method = "chat.update" if row["ts"] else "chat.postMessage"
        if row["ts"]:
            payload["ts"] = row["ts"]
        with self.db:
            self.db.execute("UPDATE slack_outbox SET attempted=? WHERE id=?", (time.time(), case))
        from .limits import reserve
        reserve(self.db, 'slack_posts', 100)
        with httpx.Client(timeout=10) as client:
            response = client.post("https://slack.com/api/" + method,
                headers={"Authorization": "Bearer " + self.c.get("SLACK_BOT_TOKEN")}, json=payload)
            response.raise_for_status()
            result = response.json()
        if not result.get("ok"):
            raise ValueError("Slack post/update rejected")
        with self.db:
            self.db.execute("UPDATE slack_outbox SET ts=? WHERE id=?", (result["ts"], case))
        read = slack_read(self.c, "conversations.history", channel=payload["channel"], latest=result["ts"], inclusive=True, limit=1)
        if not any(m.get("ts") == result["ts"] and slack_equivalent(m.get("text", ""), text) for m in read.get("messages", [])):
            raise ValueError("Slack readback unverified")
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO slack_content VALUES(?,?)', (case, content_hash))


def seed(c, db):
    c.writes()
    if db.execute("SELECT 1 FROM cases").fetchone():
        raise ValueError("Existing run: restart without connected-seed")
    client = stripe_client(c)
    if client.v1.accounts.retrieve_current().id != c.get("RP_STRIPE_ACCOUNT_ID"):
        raise ValueError("Stripe account mismatch")
    db.execute("CREATE TABLE IF NOT EXISTS seed_journal (id TEXT PRIMARY KEY, first_attempt REAL NOT NULL, payment TEXT)")
    db.commit()
    row = db.execute("SELECT * FROM seed_journal").fetchone()
    if row:
        raise ValueError("Seed already attempted; inspect/retrieve test payment before manual recovery")
    run_id = str(uuid.uuid4())
    with db:
        db.execute("INSERT INTO seed_journal VALUES(?,?,NULL)", (run_id, time.time()))
    pi = client.v1.payment_intents.create({"amount": 10000, "currency": "usd", "payment_method": "pm_card_visa",
            "payment_method_types": ["card"], "confirm": True, "metadata": {"returnpath_run": run_id}},
            {"idempotency_key": "returnpath-seed:" + run_id})
    if pi.livemode is not False or pi.status != "succeeded" or not pi.latest_charge:
        raise ValueError("Seed TEST payment not verified succeeded")
    with db:
        db.execute("UPDATE seed_journal SET payment=? WHERE id=?", (pi.id, run_id))
        db.execute("INSERT INTO cases(id,order_ref,customer,charge,original,amount,currency,policy,warehouse) VALUES(?,?,?,?,10000,3000,'usd','v1',1)",
                   ("ret-4127-" + run_id, "4127", c.get("RP_CUSTOMER_EMAIL"), pi.latest_charge))
    print("Stripe TEST fixture created. Keep this state directory for recovery. Send controlled order 4127 email.")

    from .runtime import paths
    from .warehouse import seed as seed_warehouse
    seed_warehouse(paths(c)[0].parent / 'warehouse.sqlite', "ret-4127-" + run_id)


class SlackOnly:
    """Watchdog needs only its own Slack capability; Gmail/model/Stripe may be down."""
    slack = Connected.slack

    def __init__(self, c, db):
        self.c, self.db = c, db
        c.require('SLACK_BOT_TOKEN', 'RP_SLACK_CHANNEL_ID')
        db.execute("CREATE TABLE IF NOT EXISTS slack_outbox (id TEXT PRIMARY KEY, ts TEXT, attempted REAL)")
        db.commit()
