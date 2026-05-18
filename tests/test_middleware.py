"""Tests against the real Django request pipeline.

Uses django.test.Client (not RequestFactory) so MIDDLEWARE ordering, URL
resolution, and full request/response wiring are exercised. The upstream
Prerender service is faked by patching urllib.request.urlopen — replacing
that with a real mock server is the contract-test layer.
"""
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client

BOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1)'
BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
PRERENDERED_HTML = '<html><body>prerendered</body></html>'


def _fake_urlopen(status=200, body=PRERENDERED_HTML):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.status = status
    cm.read.return_value = body.encode('utf-8')
    return cm


@pytest.fixture
def client():
    return Client()


def test_browser_passes_through(client):
    response = client.get('/', HTTP_USER_AGENT=BROWSER_UA)
    assert response.status_code == 200
    assert response.content == b'original'


def test_bot_receives_prerendered_response(client):
    with patch('urllib.request.urlopen', return_value=_fake_urlopen()):
        response = client.get('/about', HTTP_USER_AGENT=BOT_UA)
    assert response.status_code == 200
    assert PRERENDERED_HTML in response.content.decode()


def test_static_asset_with_bot_ua_passes_through(client):
    response = client.get('/style.css', HTTP_USER_AGENT=BOT_UA)
    assert response.status_code == 200
    assert response.content == b'original'


def test_escaped_fragment_triggers_prerender(client):
    with patch('urllib.request.urlopen', return_value=_fake_urlopen()):
        response = client.get('/?_escaped_fragment_=', HTTP_USER_AGENT=BROWSER_UA)
    assert response.status_code == 200
    assert PRERENDERED_HTML in response.content.decode()


def test_x_bufferbot_header_triggers_prerender(client):
    with patch('urllib.request.urlopen', return_value=_fake_urlopen()):
        response = client.get('/', HTTP_USER_AGENT=BROWSER_UA, HTTP_X_BUFFERBOT='true')
    assert response.status_code == 200
    assert PRERENDERED_HTML in response.content.decode()


def test_post_request_passes_through(client):
    response = client.post('/', HTTP_USER_AGENT=BOT_UA)
    assert response.status_code == 200
    assert response.content == b'original'


def test_network_error_falls_back_to_normal_response(client):
    with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('network error')):
        response = client.get('/', HTTP_USER_AGENT=BOT_UA)
    assert response.status_code == 200
    assert response.content == b'original'
