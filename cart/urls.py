from django.urls import path

from . import views


urlpatterns = [

    path(
        "",
        views.cart,
        name="cart"
    ),

    path(
        "increase/<int:item_id>/",
        views.increase_cart_item,
        name="increase_cart_item"
    ),

    path(
        "decrease/<int:item_id>/",
        views.decrease_cart_item,
        name="decrease_cart_item"
    ),

    path("remove/<int:item_id>/",views.remove_cart_item,name="remove_cart_item"),

]