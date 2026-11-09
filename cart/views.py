from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from core.models import Cart, CartItem

@login_required
def cart(request):
    basket, _ = Cart.objects.get_or_create(user=request.user)
    items = list(basket.items.select_related("food", "food__restaurant"))
    subtotal = sum((i.subtotal for i in items), Decimal("0.00"))
    discount = sum(((i.food.price - (i.food.discount_price if i.food.discount_price is not None else i.food.price)) * i.quantity for i in items), Decimal("0.00"))
    fee = items[0].food.restaurant.delivery_fee if items else Decimal("0.00")
    return render(request, "cart/cart.html", {"cart": basket, "cart_items": items, "subtotal": subtotal, "discount": discount, "delivery_fee": fee, "total": subtotal + fee})

@login_required
@require_POST
@transaction.atomic
def increase_cart_item(request, item_id):
    get_object_or_404(Cart.objects.select_for_update(), user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if item.quantity < 99:
        item.quantity += 1
        item.save(update_fields=["quantity"])
    else:
        messages.error(request, "Maximum quantity is 99 per item.")
    return redirect("cart")

@login_required
@require_POST
@transaction.atomic
def decrease_cart_item(request, item_id):
    get_object_or_404(Cart.objects.select_for_update(), user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save(update_fields=["quantity"])
    else:
        item.delete()
    return redirect("cart")

@login_required
@require_POST
@transaction.atomic
def remove_cart_item(request, item_id):
    get_object_or_404(Cart.objects.select_for_update(), user=request.user)
    get_object_or_404(CartItem, id=item_id, cart__user=request.user).delete()
    return redirect("cart")
