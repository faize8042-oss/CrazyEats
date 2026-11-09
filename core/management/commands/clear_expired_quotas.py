from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import RequestQuota

class Command(BaseCommand):
    help = "Remove expired abuse-protection counters; schedule daily."
    def handle(self, *args, **options):
        count, _ = RequestQuota.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(f"Removed {count} expired quota counters.")
