import copy
from returnpath.evidence import readiness, fingerprints
import pytest


def test_missing_connected_evidence_rejected():
    assert readiness({})


@pytest.mark.parametrize('fault', ['missing_app', 'mode', 'inflated', 'stale', 'broken_path', 'duplicate', 'video'])
def test_submission_negative_cases(tmp_path, fault):
    (tmp_path / 'src/returnpath').mkdir(parents=True)
    (tmp_path / 'src/returnpath/interpreter.py').write_text('fixed')
    (tmp_path / 'requirements.lock').write_text('locked')
    (tmp_path / 'artifact').write_text('synthetic checker fixture, not real evidence')
    m = {'schema_version': 1, 'verified_required_app_count': 3,
         'services': {s: {'status': 'VERIFIED_CONNECTED', 'run_id': 'test'} for s in ['gmail', 'stripe', 'slack']},
         'connected_run': {'mode': 'connected-test', 'run_id': 'test', 'refund_count': 1, 'aggregate_cents': 3000,
             **{a: True for a in ['gmail_intake','gmail_outcome_readback','stripe_refund_retrieved','slack_readback',
                                 'live_model','post_success_sigkill','restart_without_reseed']}},
         'fingerprints': fingerprints(tmp_path), 'organizer_access_confirmed': True,
         'artifacts': {k: 'artifact' for k in ['video','transcript','captions','reliability','provenance']}}
    import json
    m['provider_evidence'] = 'provider.json'
    (tmp_path / 'provider.json').write_text(json.dumps(m['connected_run']))
    assert readiness(m, tmp_path) == []  # Synthetic checker baseline; never exported as connected evidence.
    m = copy.deepcopy(m)
    if fault == 'missing_app':
        m['services']['slack']['status'] = 'NOT_RUN'
    elif fault == 'mode':
        m['connected_run']['mode'] = 'local'
    elif fault == 'inflated':
        m['verified_required_app_count'] = 4
    elif fault == 'stale':
        m['fingerprints']['implementation'] = 'old'
    elif fault == 'broken_path':
        m['artifacts']['reliability'] = 'missing'
    elif fault == 'duplicate':
        m['connected_run']['refund_count'] = 2
    elif fault == 'video':
        m['artifacts']['video'] = None
    assert readiness(m, tmp_path)
