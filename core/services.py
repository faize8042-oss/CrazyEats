from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Order, Payment
from .notifications import queue_order_notification

TRANSITIONS = {
    Order.PENDING: [Order.CONFIRMED, Order.CANCELLED],
    Order.CONFIRMED: [Order.PREPARING, Order.CANCELLED],
    Order.PREPARING: [Order.OUT_FOR_DELIVERY, Order.CANCELLED],
    Order.OUT_FOR_DELIVERY: [Order.DELIVERED],
    Order.DELIVERED: [], Order.CANCELLED: [],
}

@transaction.atomic
def transition_order(order_id, status, *, owner=None):
    queryset = Order.objects.select_for_update()
    if owner is not None:
        queryset = queryset.filter(restaurant__owner=owner)
    order = queryset.get(pk=order_id)
    if status not in TRANSITIONS.get(order.status, []):
        raise ValidationError("Invalid order status change.")
    payment = Payment.objects.filter(order=order).first()
    if status == Order.CONFIRMED and payment and payment.payment_method == "online" and payment.status != "paid":
        raise ValidationError("Online payment must be verified before accepting this order.")
    order.status = status
    if status == Order.DELIVERED:
        if payment is None:
            payment = Payment.objects.create(order=order, amount=order.total, payment_method="cod")
        if payment.payment_method == "cod":
            payment.status = "paid"
            payment.save(update_fields=["status", "updated_at"])
            order.payment_status = "paid"
    elif status == Order.CANCELLED and (payment is None or payment.status != "paid"):
        if payment:
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])
        order.payment_status = "failed"
    order.save(update_fields=["status", "payment_status", "updated_at"])
    queue_order_notification(order)
    return order
