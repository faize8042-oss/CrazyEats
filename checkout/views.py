from decimal import Decimal
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from core.models import Cart, Order, OrderItem, Payment
from core.notifications import queue_order_notification
from .forms import CheckoutForm

@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    items = list(cart.items.select_related("food", "food__restaurant", "food__category"))
    if not items:
        return redirect("cart")
    restaurant = items[0].food.restaurant
    subtotal = sum((i.subtotal for i in items), Decimal("0.00"))
    total = subtotal + restaurant.delivery_fee
    context = {"cart": cart, "cart_items": items, "restaurant": restaurant, "subtotal": subtotal, "delivery_fee": restaurant.delivery_fee, "discount": Decimal("0.00"), "total": total}
    error = None
    if any(i.food.restaurant_id != restaurant.pk for i in items):
        error = "Your cart must contain items from one restaurant."
    elif not restaurant.is_approved or not restaurant.is_open:
        error = "This restaurant is currently unavailable."
    elif any(not i.food.is_available or not i.food.category.is_active or i.quantity < 1 or i.quantity > 99 or i.subtotal < 0 for i in items):
        error = "Some items are unavailable or invalid. Please update your cart."
    elif subtotal < restaurant.minimum_order:
        context["minimum_order_error"] = True
        error = "Your cart does not meet the restaurant minimum order."
    form = CheckoutForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and not error:
        if form.is_valid():
            order = Order.objects.create(currency=settings.COMMERCE_CURRENCY, user=request.user, restaurant=restaurant, delivery_address=form.cleaned_data["address"], delivery_phone=form.cleaned_data["phone"], subtotal=subtotal, delivery_fee=restaurant.delivery_fee, total=total, notes=form.cleaned_data["instructions"])
            Payment.objects.create(order=order, amount=total, payment_method="cod")
            OrderItem.objects.bulk_create([OrderItem(order=order, food=i.food, food_name=i.food.name, price=i.food.discount_price if i.food.discount_price is not None else i.food.price, quantity=i.quantity, subtotal=i.subtotal) for i in items])
            cart.items.filter(pk__in=[i.pk for i in items]).delete()
            queue_order_notification(order)
            return redirect("order_detail", id=order.pk)
        error = " ".join(str(e) for errors in form.errors.values() for e in errors)
    context.update(error=error, form=form)
    return render(request, "checkout/checkout.html", context)
