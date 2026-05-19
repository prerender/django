# prerender-django

Django middleware for [Prerender.io](https://prerender.io). Intercepts requests from bots and crawlers and serves prerendered HTML, so your JavaScript-rendered app is fully indexable by search engines and social media scrapers.

Compatible with **Django 5+** and **Python 3.10+**.

## Installation

```bash
pip install prerender-django
```

## Setup

Add the middleware to your `settings.py`:

```python
MIDDLEWARE = [
    'prerender_django.middleware.PrerenderMiddleware',
    # ... your other middleware
]

PRERENDER_TOKEN = 'YOUR_PRERENDER_TOKEN'
```

The middleware must be placed **before** any session or authentication middleware to intercept bot requests early.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `PRERENDER_TOKEN` | `None` | Your Prerender.io token |
| `PRERENDER_SERVICE_URL` | `https://service.prerender.io/` | Prerender service URL (use this for self-hosted Prerender) |

## Self-hosted Prerender

```python
PRERENDER_SERVICE_URL = 'http://your-prerender-server:3000'
```

## How it works

Requests are prerendered when **all** of the following are true:

- The HTTP method is `GET`
- The `User-Agent` matches a known bot/crawler (Googlebot, Bingbot, Twitterbot, GPTBot, ClaudeBot, etc.)  
  — OR the URL contains `_escaped_fragment_`  
  — OR the `X-Bufferbot` header is present
- The URL does not end with a static asset extension (`.js`, `.css`, `.png`, etc.)

Everything else passes through to your normal Django views.

If the Prerender service is unreachable, the middleware falls back gracefully and serves the normal response.

## License

MIT
