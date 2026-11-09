from django.urls import path
from . import views

urlpatterns = [

    path("restaurants/", views.restaurant_list, name="restaurants"),

    path("restaurants/<int:id>/", views.restaurant_detail, name="restaurant_detail"),

    path("add-to-cart/<int:food_id>/", views.add_to_cart, name="add_to_cart"),

    path("food/<int:id>/", views.food_detail, name="food_detail"),


]
