import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger(__name__)

CRAWLER_USER_AGENTS = [
    'googlebot', 'yahoo', 'bingbot', 'baiduspider',
    'facebookexternalhit', 'twitterbot', 'rogerbot', 'linkedinbot',
    'embedly', 'quora link preview', 'showyoubot', 'outbrain',
    'pinterest', 'slackbot', 'developers.google.com/+/web/snippet',
    'w3c_validator', 'perplexity', 'oai-searchbot', 'chatgpt-user',
    'gptbot', 'claudebot', 'amazonbot',
]

EXTENSIONS_TO_IGNORE = frozenset([
    '.js', '.css', '.xml', '.less', '.png', '.jpg', '.jpeg', '.gif',
    '.pdf', '.doc', '.txt', '.ico', '.rss', '.zip', '.mp3', '.rar',
    '.exe', '.wmv', '.avi', '.ppt', '.mpg', '.mpeg', '.tif', '.wav',
    '.mov', '.psd', '.ai', '.xls', '.mp4', '.m4a', '.swf', '.dat',
    '.dmg', '.iso', '.flv', '.m4v', '.torrent', '.ttf', '.woff', '.svg',
])


def _setting(name, default=None):
    return getattr(settings, f'PRERENDER_{name}', default)


def _is_bot(user_agent):
    ua = user_agent.lower()
    return any(bot in ua for bot in CRAWLER_USER_AGENTS)


def _is_static_asset(path):
    return any(path.endswith(ext) for ext in EXTENSIONS_TO_IGNORE)


def _should_prerender(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    if not user_agent or request.method != 'GET':
        return False
    if _is_static_asset(request.path):
        return False
    if '_escaped_fragment_' in request.GET:
        return True
    if request.META.get('HTTP_X_BUFFERBOT'):
        return True
    return _is_bot(user_agent)


def _build_api_url(request):
    service_url = _setting('SERVICE_URL', 'https://service.prerender.io/')
    if not service_url.endswith('/'):
        service_url += '/'
    return f'{service_url}{request.build_absolute_uri()}'


def _fetch_prerendered(api_url, user_agent):
    token = _setting('TOKEN')
    req = urllib.request.Request(api_url)
    req.add_header('User-Agent', user_agent)
    if token:
        req.add_header('X-Prerender-Token', token)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')


class PrerenderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not _should_prerender(request):
            return self.get_response(request)

        try:
            api_url = _build_api_url(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            status, body = _fetch_prerendered(api_url, user_agent)
            return HttpResponse(body, status=status, content_type='text/html')
        except urllib.error.URLError as e:
            logger.error('Prerender error, falling back: %s', e)
            return self.get_response(request)
