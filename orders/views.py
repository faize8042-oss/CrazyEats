from core.validation import positive_id
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from core.models import Order

@login_required
def orders(request):

    user_orders = Order.objects.filter(
        user=request.user
    ).select_related(
        "restaurant"
    )

    return render(
        request,
        "orders/orders.html",
        {
            "orders": user_orders
        }
    )


@login_required
def order_detail(request, id):

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__food"
        ).select_related(
            "restaurant"
        ),
        id=id,
        user=request.user
    )

    return render(
        request,
        "orders/detail.html",
        {
            "order": order
        }
    )

@login_required
def track_order(request):

    order_id = request.GET.get("order_id")

    if order_id:

        order = get_object_or_404(
            Order.objects.select_related(
                "restaurant"
            ).prefetch_related(
                "items"
            ),
            id=positive_id(order_id),
            user=request.user
        )

    else:

        order = Order.objects.filter(
            user=request.user
        ).exclude(
            status=Order.DELIVERED
        ).exclude(
            status=Order.CANCELLED
        ).select_related(
            "restaurant"
        ).prefetch_related(
            "items"
        ).first()

    status_steps = [
        {
            "value": Order.PENDING,
            "label": "Order Placed"
        },
        {
            "value": Order.CONFIRMED,
            "label": "Confirmed"
        },
        {
            "value": Order.PREPARING,
            "label": "Preparing"
        },
        {
            "value": Order.OUT_FOR_DELIVERY,
            "label": "Out for Delivery"
        },
        {
            "value": Order.DELIVERED,
            "label": "Delivered"
        },
    ]

    if order:

        status_order = [
            Order.PENDING,
            Order.CONFIRMED,
            Order.PREPARING,
            Order.OUT_FOR_DELIVERY,
            Order.DELIVERED,
        ]

        if order.status in status_order:

            current_index = status_order.index(
                order.status
            )

        else:

            current_index = -1

        for index, step in enumerate(status_steps):

            step["completed"] = (
                current_index >= index
            )

            step["current"] = (
                order.status == step["value"]
            )

    context = {

        "order": order,

        "status_steps": status_steps,

    }

    return render(
        request,
        "orders/track.html",
        context
    )