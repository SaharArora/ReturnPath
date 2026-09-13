from fastapi.testclient import TestClient
from returnpath.preview import create_setup_app


def test_missing_config_has_useful_preview_without_exposing_app():
    client = TestClient(create_setup_app())
    assert 'Finish local setup' in client.get('/login').text
    assert 'make init-config' in client.get('/').text
    assert 'Gmail' in client.get('/credentials').text
    assert 'Stripe TEST' in client.get('/credentials').text
    assert 'Slack' in client.get('/credentials').text
    assert 'Authorizing the three real apps' in client.get('/authorization').text
    assert client.get('/cases/ret').status_code == 404
    assert client.post('/login', data={'password': 'anything'}).status_code == 405
    assert client.get('/', headers={'host': 'evil.example'}).status_code == 400
