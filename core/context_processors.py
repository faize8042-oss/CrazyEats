from django.conf import settings

def commerce(request):
    return {"currency": settings.COMMERCE_CURRENCY, "demo_mode": settings.DEMO_MODE}
