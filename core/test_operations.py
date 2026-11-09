import io
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.db import IntegrityError, transaction, DatabaseError
from django.utils import timezone
from django.core.management import call_command, CommandError
from core.models import User, RequestQuota

class OperationsTests(TestCase):
    @override_settings(REQUEST_QUOTAS={"login": (2, 60)}, TRUST_PROXY=False)
    def test_quota_shared_and_spoofed_headers_ignored(self):
        first, second = Client(), Client()
        data = {"username": "missing", "password": "wrong"}
        self.assertEqual(first.post(reverse("login"), data).status_code, 200)
        self.assertEqual(second.post(reverse("login"), data).status_code, 200)
        response = second.post(reverse("login"), data, HTTP_X_REAL_IP="1.2.3.4", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)
        self.assertEqual(response["Cache-Control"], "no-store")

    @override_settings(REQUEST_QUOTAS={"login": (1, 60)})
    def test_window_expiry_and_get_requests(self):
        data = {"username": "missing", "password": "wrong"}
        with patch("core.middleware.time.time", return_value=1200):
            self.assertEqual(self.client.get(reverse("login")).status_code, 200)
            self.assertEqual(self.client.post(reverse("login"), data).status_code, 200)
            self.assertEqual(self.client.post(reverse("login"), data).status_code, 429)
        with patch("core.middleware.time.time", return_value=1261):
            self.assertEqual(self.client.post(reverse("login"), data).status_code, 200)

    @override_settings(REQUEST_QUOTAS={"password_reset": (1, 60)})
    def test_account_limit_across_ip_addresses(self):
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            self.assertEqual(self.client.post(reverse("password_reset"), {"email": "test@example.com"}, REMOTE_ADDR="1.2.3.4").status_code, 302)
            self.assertEqual(self.client.post(reverse("password_reset"), {"email": "TEST@example.com"}, REMOTE_ADDR="2.3.4.5").status_code, 429)

    def test_recovery_email_database_constraint(self):
        User.objects.create_user("one", "Test@example.com", "SecurePassword!891")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("two", " test@EXAMPLE.com ", "SecurePassword!891")
        User.objects.create_user("blank-one", "", "SecurePassword!891")
        User.objects.create_user("blank-two", "", "SecurePassword!891")

    def test_health(self):
        self.assertEqual(self.client.get(reverse("health")).json(), {"status": "ok"})
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)
        with patch("core.health.connection.cursor", side_effect=DatabaseError("private database error")):
            response = self.client.get(reverse("health"))
            self.assertEqual(response.status_code, 503)
            self.assertNotContains(response, "private", status_code=503)

    def test_cleanup_only_expired_counters(self):
        RequestQuota.objects.create(key="old", expires_at=timezone.now()-timedelta(seconds=1))
        RequestQuota.objects.create(key="current", expires_at=timezone.now()+timedelta(hours=1))
        call_command("clear_expired_quotas", stdout=io.StringIO())
        self.assertEqual(list(RequestQuota.objects.values_list("pk", flat=True)), ["current"])

    @override_settings(DEBUG=False, DEMO_MODE=False)
    def test_demo_blocked_in_production(self):
        with self.assertRaises(CommandError): call_command("create_demo")
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=True)
    def test_launch_check_refuses_incomplete_config(self):
        with self.assertRaises(CommandError): call_command("launch_check")
