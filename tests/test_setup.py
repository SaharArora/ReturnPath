import socket

import pytest

from returnpath.auth import doctor
from returnpath.config import Config, atomic_private


def test_external_file_expansion_and_override(tmp_path):
    path = tmp_path / 'config.env'
    path.write_text("RP_MODE=connected-test\nRP_STATE_DIR=~/example\nRP_MODEL='literal $(bad)'\n")
    c = Config({'RP_ENV_FILE': str(path), 'RP_MODE': 'local'})
    assert c.get('RP_MODE') == 'local'
    assert c.path_value('RP_STATE_DIR', '').is_absolute()
    assert c.get('RP_MODEL') == 'literal $(bad)'


def test_private_file(tmp_path):
    p = tmp_path / 'token'
    atomic_private(p, 'synthetic')
    assert p.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize('service', ['gmail', 'slack', 'stripe', 'model'])
def test_doctor_missing_is_blocked(service):
    assert doctor(Config({'RP_ENV_FILE': '/dev/null'}), service)['status'] == 'BLOCKED'


def test_local_network_isolation():
    with socket.socket() as s, pytest.raises(PermissionError):
        s.connect(('8.8.8.8', 443))
