from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from restaurant_dashboard.views import restaurant_orders
from core.health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("", include("admin_dashboard.urls")),
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
    path("", include("accounts.urls")),
    path("", include("restaurants.urls")),
    path("cart/", include("cart.urls")),
    path("", include("checkout.urls")),
    path("", include("orders.urls")),
    path("", include("restaurant_dashboard.urls")),
    path("restaurant/dashboard/orders/", restaurant_orders),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
