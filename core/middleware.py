import hashlib
import hmac
import time
from datetime import datetime, timezone
from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.urls import resolve, Resolver404
from .models import RequestQuota

class RequestQuotaMiddleware:
    """Database-shared fixed windows, independent of web-worker count."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != "POST":
            return self.get_response(request)
        try:
            route = resolve(request.path_info).url_name
        except Resolver404:
            return self.get_response(request)
        rules = settings.REQUEST_QUOTAS.get(route)
        if not rules:
            return self.get_response(request)
        client = request.META.get("REMOTE_ADDR", "unknown")
        if settings.TRUST_PROXY:
            # Bundled proxy overwrites X-Real-IP. Backend must remain private.
            client = request.META.get("HTTP_X_REAL_IP", client)
        limit, seconds = rules
        timestamp = int(time.time())
        bucket = timestamp // seconds
        identities = ["ip:" + client]
        if route == "checkout" and request.user.is_authenticated:
            identities = ["user:" + str(request.user.pk)]
        elif route in ("login", "password_reset"):
            identity = request.POST.get("username" if route == "login" else "email", "").strip().casefold()[:254]
            if identity:
                identities.append("account:" + identity)
        for identity in identities:
            key = hmac.new(settings.SECRET_KEY.encode(), f"{route}:{bucket}:{identity}".encode(), hashlib.sha256).hexdigest()
            quota, _ = RequestQuota.objects.get_or_create(key=key, defaults={"expires_at": datetime.fromtimestamp((bucket + 1) * seconds, timezone.utc)})
            accepted = RequestQuota.objects.filter(pk=quota.pk, count__lt=limit).update(count=F("count") + 1)
            if not accepted:
                response = HttpResponse("Too many attempts. Please wait and try again.", status=429, content_type="text/plain")
                response["Retry-After"] = str((bucket + 1) * seconds - timestamp)
                response["Cache-Control"] = "no-store"
                return response
        return self.get_response(request)
