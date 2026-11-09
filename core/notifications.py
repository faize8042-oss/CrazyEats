from .models import EmailNotification

def queue_order_notification(order):
    if not order.user.email:
        return
    EmailNotification.objects.get_or_create(
        event_key=f"order:{order.pk}:{order.status}:{order.payment_status}",
        defaults={"recipient": order.user.email, "subject": f"CrazyEats order #{order.pk}: {order.get_status_display()}", "body": f"Your order #{order.pk} from {order.restaurant.name} is {order.get_status_display().lower()}. Total: {order.currency} {order.total}. Payment: {order.get_payment_status_display()}. Sign in to CrazyEats to view your order."},
    )
