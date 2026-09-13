"""Repeatable narrow resolution evaluation; offline control and live results are distinct."""
import argparse
import json
import tempfile
import time
from pathlib import Path

from returnpath.config import Config
from returnpath import resolution as r

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
parser.add_argument('--trials', type=int, default=10)
args = parser.parse_args()
if not 1 <= args.trials <= 20:
    parser.error('trials must be 1–20')
c = Config()
if args.live:
    if c.get('RP_MODE') != 'connected-test':
        parser.error('live evaluation requires connected-test configuration')
    c.values['RP_RESOLUTION_MODEL'] = 'live'
else:
    from returnpath.isolation import install
    install()
    c.values['RP_RESOLUTION_MODEL'] = 'stub'
cases = [
    ('keep', 'I want to keep the item and get a refund', 'keep'),
    ('return', 'I want to return the item for a refund', 'return'),
    ('clarify', 'Something is wrong. What options do I have?', None),
]
rows = []
started = time.time()
with tempfile.TemporaryDirectory(prefix='returnpath-resolution-eval-') as root:
    for scenario, request, expected in cases:
        for trial in range(args.trials):
            db = r.connect(Path(root) / f'{scenario}-{trial}.sqlite')
            rid = r.start(db, 'synthetic-customer', r.catalog(c), '7202')
            try:
                r.negotiate(db, c, rid, 'synthetic-customer', request)
                offer = db.execute('SELECT terms FROM offers').fetchone()
                state = db.execute('SELECT state FROM resolutions').fetchone()[0]
                actual = json.loads(offer[0])['selected']['id'] if offer else None
                passed = actual == expected and (state == 'CLARIFY' if expected is None else state == 'OFFERED')
                rows.append({'scenario': scenario, 'trial': trial + 1, 'passed': passed, 'state': state})
            except Exception as exc:
                rows.append({'scenario': scenario, 'trial': trial + 1, 'passed': False, 'error_type': type(exc).__name__})
            finally:
                db.close()
report = {'mode': 'LIVE_MODEL' if args.live else 'DETERMINISTIC_OFFLINE_BASELINE',
          'model': c.get('RP_MODEL') if args.live else 'stub', 'revision': r.REVISION,
          'scope': 'Three preference/clarification scenarios; not a security or crash benchmark',
          'episodes': len(rows), 'passed': sum(row['passed'] for row in rows),
          'elapsed_seconds': round(time.time() - started, 2), 'results': rows}
path = Path('.runtime/resolution-' + ('live' if args.live else 'offline') + '-evaluation.json')
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != 'results'}, indent=2))
print('Report:', path)
raise SystemExit(int(report['passed'] != report['episodes']))
