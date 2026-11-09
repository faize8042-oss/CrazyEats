from django.urls import path
from . import views

urlpatterns = [

    path("orders/",views.orders,name="orders"),

    path("orders/<int:id>/", views.order_detail, name="order_detail"),

    path("orders/track/",views.track_order,name="track_order"),

]