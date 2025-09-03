from django.conf import settings
from django.http import HttpResponseRedirect


def index(request):
    if request.method == "GET":
        return HttpResponseRedirect(settings.HONEYPOT_URL)
