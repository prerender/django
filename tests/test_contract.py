"""Contract tests for django integration against the shared mock server.

Spec: https://github.com/prerender/integration-contract
"""

import re

from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from prerender_django.middleware import PrerenderMiddleware
from .conftest import get_recorded

BOT_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1)'
BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
TOKEN = 'test-token-abc123'
UUID_V4 = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

factory = RequestFactory()


def _normal_response(_request):
    return HttpResponse('original')


def _call(middleware, path, headers=None, query=None):
    request = factory.get(path, query or {}, **(headers or {}))
    return middleware(request)


def test_bot_request_emits_outgoing_request_with_required_headers(mock_server):
    with override_settings(PRERENDER_SERVICE_URL=f'{mock_server}/', PRERENDER_TOKEN=TOKEN):
        middleware = PrerenderMiddleware(_normal_response)
        _call(middleware, '/blog/post-1', headers={'HTTP_USER_AGENT': BOT_UA})

    recorded = get_recorded(mock_server)
    assert len(recorded) == 1
    r = recorded[0]
    assert r['method'] == 'GET'
    assert r['url'].endswith('/blog/post-1')
    assert r['headers']['user-agent'] == BOT_UA
    assert r['headers']['x-prerender-token'] == TOKEN
    assert r['headers']['x-prerender-int-type'] == 'Django'
    assert re.match(r'^\d+\.\d+\.\d+', r['headers']['x-prerender-int-version'])
    assert UUID_V4.match(r['headers']['x-prerender-request-id'])


def test_browser_request_emits_no_outgoing_request(mock_server):
    with override_settings(PRERENDER_SERVICE_URL=f'{mock_server}/', PRERENDER_TOKEN=TOKEN):
        middleware = PrerenderMiddleware(_normal_response)
        _call(middleware, '/', headers={'HTTP_USER_AGENT': BROWSER_UA})

    assert get_recorded(mock_server) == []


def test_static_asset_with_bot_ua_emits_no_outgoing_request(mock_server):
    with override_settings(PRERENDER_SERVICE_URL=f'{mock_server}/', PRERENDER_TOKEN=TOKEN):
        middleware = PrerenderMiddleware(_normal_response)
        _call(middleware, '/style.css', headers={'HTTP_USER_AGENT': BOT_UA})

    assert get_recorded(mock_server) == []


def test_token_omitted_when_unconfigured(mock_server):
    with override_settings(PRERENDER_SERVICE_URL=f'{mock_server}/', PRERENDER_TOKEN=None):
        middleware = PrerenderMiddleware(_normal_response)
        _call(middleware, '/', headers={'HTTP_USER_AGENT': BOT_UA})

    recorded = get_recorded(mock_server)
    assert len(recorded) == 1
    assert 'x-prerender-token' not in recorded[0]['headers']


def test_escaped_fragment_triggers_prerender_for_browser_ua(mock_server):
    with override_settings(PRERENDER_SERVICE_URL=f'{mock_server}/', PRERENDER_TOKEN=TOKEN):
        middleware = PrerenderMiddleware(_normal_response)
        _call(middleware, '/', query={'_escaped_fragment_': ''}, headers={'HTTP_USER_AGENT': BROWSER_UA})

    recorded = get_recorded(mock_server)
    assert len(recorded) == 1
    assert '_escaped_fragment_' in recorded[0]['url']


def test_request_id_is_unique_per_outgoing_request(mock_server):
    with override_settings(PRERENDER_SERVICE_URL=f'{mock_server}/', PRERENDER_TOKEN=TOKEN):
        middleware = PrerenderMiddleware(_normal_response)
        _call(middleware, '/', headers={'HTTP_USER_AGENT': BOT_UA})
        _call(middleware, '/', headers={'HTTP_USER_AGENT': BOT_UA})

    recorded = get_recorded(mock_server)
    assert len(recorded) == 2
    assert (
        recorded[0]['headers']['x-prerender-request-id']
        != recorded[1]['headers']['x-prerender-request-id']
    )
