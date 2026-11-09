from django.urls import path
from . import views

urlpatterns = [

    path("admin/dashboard/",views.dashboard,name="admin_dashboard"),

   path("admin/users/",views.users,name="admin_users"),

    path("admin/restaurants/",views.restaurants,name="admin_restaurants"),

    path("admin/orders/",views.orders,name="admin_orders"),

    path("admin/analytics/",views.analytics,name="admin_analytics"),

]
