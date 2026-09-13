"""Generate measured offline test report, with no provider credentials or raw input."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from returnpath.evidence import fingerprints

root = Path(__file__).resolve().parents[1]
raw = root / '.runtime' / 'evaluation'
raw.mkdir(parents=True, exist_ok=True)
env = {**os.environ, 'RP_ENV_FILE': '/dev/null', 'RP_MODE': 'local', 'RP_ALLOW_CONNECTED_WRITES': 'false'}
result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--junitxml=' + str(raw / 'pytest.xml')], cwd=root, env=env)
xml = ET.parse(raw / 'pytest.xml')
cases = xml.findall('.//testcase')
report = {'run_id': str(uuid.uuid4()), 'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'mode': 'local', 'adapters': ['persistent fake payment', 'persistent fake mail', 'persistent fake Slack', 'stub model'],
          'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
          'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip()),
          'fingerprints': fingerprints(), 'tests': len(cases),
          'failed': len(xml.findall('.//failure')), 'errors': len(xml.findall('.//error')),
          'skipped': len(xml.findall('.//skipped')), 'elapsed_seconds': sum(float(c.get('time', 0)) for c in cases),
          'nodes': [{'node': c.get('classname') + '::' + c.get('name'), 'seconds': float(c.get('time', 0)),
                     'status': 'FAILED' if c.find('failure') is not None or c.find('error') is not None else 'SKIPPED' if c.find('skipped') is not None else 'PASSED'} for c in cases],
          'connected_workflow': 'NOT_RUN', 'live_model': 'NOT_RUN',
          'limitations': ['Test counts are not exhaustive scenario-family coverage or a proof.',
                          'No connected provider effects or genuine video recorded.']}
output = root / 'evidence'
output.mkdir(exist_ok=True)
(output / 'offline-evaluation.json').write_text(json.dumps(report, indent=2) + '\n')
(output / 'offline-evaluation.md').write_text('# Actual offline evaluation\n\nRun `' + report['run_id'] + '`; mode LOCAL SIMULATORS.\n\n'
    + str(report['tests']) + ' tests; ' + str(report['failed']) + ' failures; ' + str(report['errors']) + ' errors; '
    + str(report['skipped']) + ' skipped. These are test-node counts, not a recovery success percentage.\n\n'
    + 'See [machine-readable results](offline-evaluation.json) for exact nodes, durations and fingerprints. Connected workflow and live model: NOT_RUN.\n')
manifest = json.loads((root / 'submission.json').read_text())
manifest['fingerprints'] = report['fingerprints']
(root / 'submission.json').write_text(json.dumps(manifest, indent=2) + '\n')
raise SystemExit(result.returncode)
