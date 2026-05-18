from django.http import HttpResponse
from django.urls import re_path


def _original(request):
    return HttpResponse('original')


urlpatterns = [
    re_path(r'^.*$', _original),
]
