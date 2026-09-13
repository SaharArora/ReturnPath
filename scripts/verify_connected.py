"""Read-only ordinary-run evidence collection. Never issues payments or messages."""
import base64
import datetime
import email
import hashlib
import json
import re
import sqlite3
from email.policy import default
from pathlib import Path

from returnpath.auth import gmail, slack_read
from returnpath.config import Config
from returnpath.oracle import stripe_records

c = Config()
if c.get('RP_MODE') != 'connected-test':
    raise SystemExit('BLOCKED: connected-test configuration required')
root = c.path_value('RP_STATE_DIR', '~/.local/share/returnpath') / 'connected-test'
db = sqlite3.connect('file:' + str(root / 'app.sqlite') + '?mode=ro', uri=True)
db.row_factory = sqlite3.Row
rows = db.execute('SELECT c.id,c.charge,o.id AS operation,o.provider_id FROM cases c JOIN operations o ON o.case_id=c.id').fetchall()
if len(rows) != 1:
    raise SystemExit('BLOCKED: expected one scoped connected fixture')
case = rows[0]
stripe = stripe_records(c, case['charge'], case['operation'], case['id'])
api = gmail(c)
contacts = db.execute("SELECT event FROM contacts WHERE case_id=? AND channel='gmail' AND verified=1", (case['id'],)).fetchall()
intake = False
for contact in contacts:
    message = api.users().messages().get(userId='me', id=contact['event'], format='metadata').execute(num_retries=0)
    headers = {h['name'].lower(): h['value'] for h in message.get('payload', {}).get('headers', [])}
    intake |= email.utils.parseaddr(headers.get('from', ''))[1] == c.get('RP_CUSTOMER_EMAIL') and 'SENT' not in message.get('labelIds', [])
notification = db.execute('SELECT * FROM notifications WHERE case_id=?', (case['id'],)).fetchone()
outcome = False
message_id_preserved = False
if notification and notification['provider_id']:
    result = api.users().messages().get(userId='me', id=notification['provider_id'], format='raw').execute(num_retries=0)
    msg = email.message_from_bytes(base64.urlsafe_b64decode(result['raw']), policy=default)
    part = msg.get_body(preferencelist=('plain',))
    expected_id = '<' + hashlib.sha256(('refund-status:' + case['operation']).encode()).hexdigest() + '@returnpath.invalid>'
    message_id_preserved = msg['Message-ID'] == expected_id
    outcome = bool(part and 'SENT' in result.get('labelIds', []) and result.get('id') == notification['provider_id']
                   and email.utils.parseaddr(msg['To'])[1] == c.get('RP_CUSTOMER_EMAIL')
                   and re.sub(r'\s+', ' ', part.get_content()).strip() == re.sub(r'\s+', ' ', notification['body']).strip())
slack = False
post = db.execute('SELECT ts FROM slack_outbox WHERE id=?', (case['id'],)).fetchone()
if post and post['ts']:
    result = slack_read(c, 'conversations.history', channel=c.get('RP_SLACK_CHANNEL_ID'), latest=post['ts'], inclusive=True, limit=1)
    for message in result.get('messages', []):
        if message.get('ts') != post['ts']:
            continue
        lines = message.get('text', '').splitlines()
        try:
            data = json.loads(lines[1])
            slack = (lines[0] == 'ReturnPath TEST | ' + case['id'] and data.get('operation') == case['operation']
                     and data.get('refund') == case['provider_id'] and data.get('notification') == 'SUBMITTED'
                     and data.get('remaining') == 'No automatic financial action')
        except (ValueError, IndexError):
            pass
live_model = db.execute("SELECT 1 FROM audit WHERE case_id=? AND kind='INTERPRETATION' AND json_extract(data,'$.model') != 'DETERMINISTIC_STUB'", (case['id'],)).fetchone() is not None
report = {'run_id': 'connected-' + hashlib.sha256(case['id'].encode()).hexdigest()[:16],
          'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'mode': 'connected-test',
          'gmail_intake': bool(intake), 'gmail_outcome_readback': bool(outcome), 'slack_readback': bool(slack),
          'stripe_refund_retrieved': stripe['passed'], 'live_model': live_model,
          'refund_count': stripe['refund_count'], 'aggregate_cents': stripe['aggregate_cents'],
          'gmail_supplied_message_id_preserved': message_id_preserved,
          'post_success_sigkill': False, 'restart_without_reseed': False,
          'limitations': ['Ordinary run only; connected crash experiment not performed',
                          'Live-model provenance from durable application audit; provider outcomes separately retrieved',
                          'Warehouse evidence simulated; TEST payment, no real cash settlement',
                          'Gmail readback uses the acknowledged provider ID; supplied Message-ID was not preserved, so ambiguous-send lookup remains unverified']}
report['ordinary_run_passed'] = all(report[k] for k in ['gmail_intake', 'gmail_outcome_readback', 'slack_readback', 'stripe_refund_retrieved', 'live_model'])
path = Path('evidence/connected-ordinary-run.json')
path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
raise SystemExit(int(not report['ordinary_run_passed']))
