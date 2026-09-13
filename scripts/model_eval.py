import json
from pathlib import Path
import sys
from returnpath.config import Config
from returnpath.interpreter import interpret

root = Path(__file__).resolve().parents[1]
c = Config()
if c.get('RP_MODE') != 'connected-test' or not c.get('OPENAI_API_KEY') or not c.get('RP_MODEL'):
    print('BLOCKED: live model evaluation needs connected-test mode and separately configured API key/model')
    raise SystemExit(1)
rows = []
for fixture in json.loads((root / 'fixtures/interpreter.json').read_text()):
    try:
        result = interpret(c, fixture['text'])
        rows.append({'fixture': fixture['id'], 'output': result.model_dump(),
                     'passed': result.order_reference == fixture['reference']})
    except Exception as exc:
        rows.append({'fixture': fixture['id'], 'error': type(exc).__name__, 'passed': False})
path = root / '.runtime/live-model-evaluation.json'
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps({'model': c.get('RP_MODEL'), 'prompt_revision': 'v1', 'fixture_revision': 'v1', 'results': rows}, indent=2))
print('Live model evaluation completed; local raw report requires review before export.')
sys.exit(int(any(not row['passed'] for row in rows)))
