from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.utils import timezone
from datetime import timedelta
from core.models import EmailNotification

class Command(BaseCommand):
    help = "Check launch configuration without sending email, charging payments, or exposing secrets."
    def handle(self, *args, **options):
        issues = []
        if settings.DEBUG: issues.append("DEBUG is enabled")
        if settings.DEMO_MODE: issues.append("DEMO_MODE is enabled")
        if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql": issues.append("Production database is not PostgreSQL")
        if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER: issues.append("SMTP host/account is missing")
        if "localhost" in settings.DEFAULT_FROM_EMAIL: issues.append("Sender address is not configured")
        if not settings.OPERATOR_NAME or not settings.SUPPORT_EMAIL: issues.append("Operator identity/support email is missing")
        if not settings.CSRF_TRUSTED_ORIGINS: issues.append("Trusted HTTPS origin is missing")
        if EmailNotification.objects.filter(sent_at__isnull=True, created_at__lt=timezone.now()-timedelta(minutes=15)).exists(): issues.append("Email queue has messages older than 15 minutes")
        if issues:
            raise CommandError("Launch blocked: " + "; ".join(issues))
        call_command("check", deploy=True, fail_level="WARNING")
        self.stdout.write("Configuration checks passed. Real SMTP, HTTPS, payment, backup restore, browser and load acceptance are still required.")
