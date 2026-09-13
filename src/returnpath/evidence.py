"""Project-defined consistency/readiness gate, not provider authentication."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fingerprints(root=ROOT):
    def digest(paths):
        h = hashlib.sha256()
        for p in sorted(paths):
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
        return h.hexdigest()
    code = [*list((root / 'src').rglob('*.py')), *list((root / 'tests').rglob('*.py')),
            *list((root / 'scripts').rglob('*.py')), *list((root / 'fixtures').glob('*.json'))]
    code += [root / name for name in ('Makefile', 'pyproject.toml') if (root / name).is_file()]
    return {'implementation': digest(code),
            'lock': digest([root / 'requirements.lock']),
            'prompt_schema': digest([root / 'src/returnpath/interpreter.py'])}


def readiness(manifest, root=ROOT):
    errors = []
    if manifest.get('schema_version') != 1:
        errors.append('manifest schema_version')
    services = manifest.get('services', {})
    verified = [name for name in ['gmail', 'stripe', 'slack']
                if services.get(name, {}).get('status') == 'VERIFIED_CONNECTED']
    if manifest.get('verified_required_app_count') != len(verified):
        errors.append('contradictory app count')
    if len(verified) != 3:
        errors.append('three actual services not verified')
    connected = manifest.get('connected_run')
    if not isinstance(connected, dict):
        errors.append('connected same-run evidence missing')
    else:
        if connected.get('mode') != 'connected-test':
            errors.append('contradictory connected mode')
        if not connected.get('run_id') or any(services.get(s, {}).get('run_id') != connected.get('run_id') for s in verified):
            errors.append('service run mismatch')
        if connected.get('refund_count') != 1 or connected.get('aggregate_cents') != 3000:
            errors.append('provider refund invariant')
        for action in ['gmail_intake', 'gmail_outcome_readback', 'stripe_refund_retrieved', 'slack_readback',
                       'live_model', 'post_success_sigkill', 'restart_without_reseed']:
            if connected.get(action) is not True:
                errors.append('missing action: ' + action)
    provider_path = manifest.get('provider_evidence')
    if not isinstance(provider_path, str) or not (root / provider_path).is_file():
        errors.append('provider evidence artifact missing')
    else:
        try:
            recorded = json.loads((root / provider_path).read_text())
            if recorded != connected:
                errors.append('provider evidence disagrees with manifest')
        except (ValueError, OSError):
            errors.append('malformed provider evidence')
    if manifest.get('fingerprints') != fingerprints(root):
        errors.append('stale implementation/lock/prompt fingerprint')
    for key in ['video', 'transcript', 'captions', 'reliability', 'provenance']:
        path = manifest.get('artifacts', {}).get(key)
        if not isinstance(path, str) or not path or not (root / path).is_file() or not (root / path).resolve().is_relative_to(root.resolve()):
            errors.append('missing or unsafe artifact: ' + key)
    if manifest.get('organizer_access_confirmed') is not True:
        errors.append('organizer private-access/eligibility unresolved')
    return errors


def check(strict=False):
    manifest = json.loads((ROOT / 'submission.json').read_text())
    if strict:
        errors = readiness(manifest)
    else:
        errors = []
        report = ROOT / manifest['offline_report']
        data = json.loads(report.read_text())
        import re
        named = {family for node in data['nodes'] for family in re.findall(r'F[0-9]{2}', node['node'])}
        if not {f'F{i:02}' for i in range(1, 31)}.issubset(named):
            errors.append('required named offline families missing')
        if data['tests'] != len(data['nodes']):
            errors.append('offline count mismatch')
        if data['failed'] or data['errors'] or not data['tests']:
            errors.append('offline evaluation failed or empty')
        if data['fingerprints'] != fingerprints():
            errors.append('offline report is stale')
        demo = json.loads((ROOT / 'evidence/local-demo.json').read_text())
        if demo.get('fingerprints') != fingerprints() or not demo.get('run_id'):
            errors.append('local demo snapshot missing or stale')
        if demo.get('refund_count') != 1 or demo.get('aggregate_cents') != 3000:
            errors.append('local demo provider invariant failed')
        if manifest['verified_required_app_count'] != sum(v['status'] == 'VERIFIED_CONNECTED' for v in manifest['services'].values()):
            errors.append('contradictory service count')
        if manifest['fingerprints'] != fingerprints():
            errors.append('manifest is stale')
        for path in manifest['evidence_index']:
            if not (ROOT / path).is_file():
                errors.append('broken evidence path: ' + path)
    print(json.dumps({'status': 'BLOCKED' if errors else ('SUBMISSION_READY' if strict else 'LOCAL_REVIEW_CHECK_PASSED'), 'errors': errors}, indent=2))
    return int(bool(errors))
