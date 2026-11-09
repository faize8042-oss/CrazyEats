from django.urls import path
from . import views
from restaurant_dashboard.views import (
    category_management,
    add_category,
)

from restaurant_dashboard.views import restaurant_settings

urlpatterns = [

    path(
        "restaurant/dashboard/",
        views.dashboard,
        name="restaurant_dashboard"
    ),

    path(
        "restaurant/menu/",
        views.menu_management,
        name="restaurant_menu"
    ),

    path(
        "restaurant/menu/add/",
        views.add_food,
        name="add_food"
    ),

    path(
        "restaurant/menu/edit/<int:id>/",
        views.edit_food,
        name="edit_food"
    ),

    path(
        "restaurant/menu/delete/<int:id>/",
        views.delete_food,
        name="delete_food"
    ),

    path(
        "restaurant/categories/",
        category_management,
        name="category_management"
    ),

    path(
        "restaurant/categories/add/",
        add_category,
        name="add_category"
    ),

    path(
        "restaurant/settings/",
        restaurant_settings,
        name="restaurant_settings"
    ),

    path(
        "restaurant/orders/",
        views.restaurant_orders,
        name="restaurant_orders"
    ),



    path(
        "restaurant/dashboard/orders/<int:id>/status/",
        views.update_order_status,
        name="update_order_status"
    ),

    path(
        "restaurant/orders/<int:id>/",
        views.restaurant_order_detail,
        name="restaurant_order_detail"
    ),

    path(
        "analytics/",
        views.restaurant_analytics,
        name="restaurant_analytics"
    ),
]
