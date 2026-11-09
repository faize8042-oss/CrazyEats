from django.core.management.base import BaseCommand
from django.core import mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from core.models import EmailNotification
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Deliver queued notifications. Schedule every minute; failures remain queued for retry."

    def handle(self, *args, **options):
        sent = 0
        ids = list(EmailNotification.objects.filter(sent_at__isnull=True).values_list("pk", flat=True)[:100])
        for pk in ids:
            with transaction.atomic():
                item = EmailNotification.objects.select_for_update().get(pk=pk)
                if item.sent_at:
                    continue
                item.attempts += 1
                try:
                    delivered = mail.send_mail(item.subject, item.body, settings.DEFAULT_FROM_EMAIL, [item.recipient])
                    if delivered != 1:
                        raise RuntimeError("Email backend did not accept the notification")
                except Exception as exc:
                    item.last_error = type(exc).__name__
                    logger.warning("Notification %s delivery failed (%s)", item.pk, type(exc).__name__)
                else:
                    item.sent_at = timezone.now()
                    item.last_error = ""
                    sent += 1
                item.save(update_fields=["attempts", "last_error", "sent_at"])
        self.stdout.write(f"Delivered {sent} notifications.")
