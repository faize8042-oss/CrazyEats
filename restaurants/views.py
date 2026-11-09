from django.db.models import Q, Prefetch
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from core.models import Restaurant, Food, Cart, CartItem,Category,Order


def restaurant_list(request):

    restaurants = Restaurant.objects.filter(
        is_approved=True
    )

    query = request.GET.get("q", "").strip()[:100]
    category = request.GET.get("category", "").strip()[:100]
    if query:
        restaurants = restaurants.filter(Q(name__icontains=query) | Q(foods__name__icontains=query, foods__is_available=True, foods__category__is_active=True)).distinct()
    if category:
        restaurants = restaurants.filter(categories__name__iexact=category, categories__is_active=True).distinct()
    if request.GET.get("open") == "1":
        restaurants = restaurants.filter(is_open=True)
    return render(
        request,
        "restaurants/list.html",
        {
            "restaurants": restaurants, "q": query, "selected_category": category
        }
    )


def restaurant_detail(request, id):

    restaurant = get_object_or_404(
        Restaurant.objects.prefetch_related(
            "categories__foods"
        ),
        id=id,
        is_approved=True
    )

    categories = restaurant.categories.filter(is_active=True).prefetch_related(Prefetch("foods", queryset=Food.objects.filter(is_available=True)))

    return render(
        request,
        "restaurants/detail.html",
        {
            "restaurant": restaurant,
            "categories": categories,
        }
    )

def food_detail(request, id):

    food = get_object_or_404(
        Food.objects.select_related(
            "restaurant",
            "category"
        ),
        id=id,
        is_available=True,
        restaurant__is_approved=True,
        category__is_active=True
    )

    return render(
        request,
        "restaurants/food_detail.html",
        {
            "food": food
        }
    )

@login_required
@require_POST
@transaction.atomic
def add_to_cart(request, food_id):

    food = get_object_or_404(
        Food,
        id=food_id,
        is_available=True,
        restaurant__is_approved=True,
        category__is_active=True
    )

    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    if not food.restaurant.is_open:
        messages.error(request, "This restaurant is closed.")
        return redirect("cart")

    # Check if cart already contains food
    # from another restaurant
    existing_item = cart.items.first()

    if existing_item:

        if existing_item.food.restaurant_id != food.restaurant_id:

            messages.error(request, "Your cart can only contain items from one restaurant. Remove existing items first.")
            return redirect("cart")

    # Add food to cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        food=food
    )

    if not created:

        cart_item.quantity = min(cart_item.quantity + 1, 99)

    cart_item.save()

    return redirect("cart")
