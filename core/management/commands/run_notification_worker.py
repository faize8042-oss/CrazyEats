import time
from django.core.management import BaseCommand, call_command
from django.db import close_old_connections

class Command(BaseCommand):
    help = "Run the notification outbox every minute. Stop with Ctrl+C."
    def handle(self, *args, **options):
        try:
            while True:
                close_old_connections()
                call_command("send_notifications")
                time.sleep(60)
        except KeyboardInterrupt:
            return
