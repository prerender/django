import urllib.error
from unittest.mock import MagicMock, patch

from django.http import HttpResponse
from django.test import RequestFactory

from prerender_django.middleware import PrerenderMiddleware

BOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1)'
BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
PRERENDERED_HTML = '<html><body>prerendered</body></html>'

factory = RequestFactory()


def normal_response(_request):
    return HttpResponse('original')


def mock_urlopen(status=200, body=PRERENDERED_HTML):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.status = status
    cm.read.return_value = body.encode('utf-8')
    return cm


def test_browser_passes_through():
    middleware = PrerenderMiddleware(normal_response)
    request = factory.get('/', HTTP_USER_AGENT=BROWSER_UA)
    response = middleware(request)
    assert response.status_code == 200
    assert response.content == b'original'


def test_bot_receives_prerendered_response():
    middleware = PrerenderMiddleware(normal_response)
    request = factory.get('/', HTTP_USER_AGENT=BOT_UA)
    with patch('urllib.request.urlopen', return_value=mock_urlopen()):
        response = middleware(request)
    assert response.status_code == 200
    assert PRERENDERED_HTML in response.content.decode()


def test_static_asset_with_bot_ua_passes_through():
    middleware = PrerenderMiddleware(normal_response)
    request = factory.get('/style.css', HTTP_USER_AGENT=BOT_UA)
    response = middleware(request)
    assert response.status_code == 200
    assert response.content == b'original'


def test_escaped_fragment_triggers_prerender():
    middleware = PrerenderMiddleware(normal_response)
    request = factory.get('/', {'_escaped_fragment_': ''}, HTTP_USER_AGENT=BROWSER_UA)
    with patch('urllib.request.urlopen', return_value=mock_urlopen()):
        response = middleware(request)
    assert response.status_code == 200
    assert PRERENDERED_HTML in response.content.decode()


def test_network_error_falls_back_to_normal_response():
    middleware = PrerenderMiddleware(normal_response)
    request = factory.get('/', HTTP_USER_AGENT=BOT_UA)
    with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('network error')):
        response = middleware(request)
    assert response.status_code == 200
    assert response.content == b'original'
