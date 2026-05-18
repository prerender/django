SECRET_KEY = 'test-secret-key'
DATABASES = {}
INSTALLED_APPS = []

ROOT_URLCONF = 'tests.urls'

MIDDLEWARE = [
    'prerender_django.middleware.PrerenderMiddleware',
]

ALLOWED_HOSTS = ['*']
