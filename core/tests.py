from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core import mail
from django.core.management import call_command
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.exceptions import ValidationError
from core.models import User, Restaurant, Category, Food, Cart, CartItem, Order, Payment, EmailNotification
from core.services import transition_order
from restaurant_dashboard.forms import FoodForm

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CommerceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user("customer", "customer@example.com", "SecurePassword!891")
        cls.other = User.objects.create_user("other", "other@example.com", "SecurePassword!891")
        cls.owner = User.objects.create_user("owner", "owner@example.com", "SecurePassword!891", role="restaurant")
        cls.admin = User.objects.create_superuser("boss", "boss@example.com", "SecurePassword!891")
        cls.restaurant = Restaurant.objects.create(owner=cls.owner, name="Test Kitchen", address="Lahore", phone="03001234567", email="kitchen@example.com", opening_time="09:00", closing_time="23:00", is_approved=True, delivery_fee=Decimal("100"))
        cls.category = Category.objects.create(restaurant=cls.restaurant, name="Burgers")
        cls.food = Food.objects.create(restaurant=cls.restaurant, category=cls.category, name="Zinger", price=Decimal("500"), discount_price=Decimal("400"))

    def setUp(self):
        self.client.force_login(self.customer)
        self.cart = Cart.objects.create(user=self.customer)
        self.item = CartItem.objects.create(cart=self.cart, food=self.food, quantity=2)
        self.payload = {"address": "House 12, Main Road, Lahore", "phone": "03001234567", "payment_method": "cod"}

    def place(self):
        self.assertEqual(self.client.post(reverse("checkout"), self.payload).status_code, 302)
        return Order.objects.get()

    def test_registration(self):
        self.client.logout()
        data = {"username": "new", "email": "new@example.com", "password1": "UniquePassword!9944", "password2": "UniquePassword!9944", "role": "admin", "is_staff": "true"}
        self.assertEqual(self.client.post(reverse("register"), data).status_code, 302)
        user = User.objects.get(username="new")
        self.assertEqual(user.role, "customer")
        self.assertFalse(user.is_staff)

    def test_registration_requires_email(self):
        self.client.post(reverse("register"), {"username": "new", "password1": "UniquePassword!9944", "password2": "UniquePassword!9944"})
        self.assertFalse(User.objects.filter(username="new").exists())

    def test_checkout_and_replay(self):
        order = self.place()
        self.assertEqual(order.total, Decimal("900"))
        self.assertEqual(order.currency, "PKR")
        self.assertEqual(order.items.get().price, Decimal("400"))
        self.assertEqual(order.payment.amount, order.total)
        self.assertFalse(self.cart.items.exists())
        self.assertEqual(EmailNotification.objects.count(), 1)
        self.client.post(reverse("checkout"), self.payload)
        self.assertEqual(Order.objects.count(), 1)

    def test_checkout_rollback(self):
        with patch("checkout.views.OrderItem.objects.bulk_create", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("checkout"), self.payload)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Payment.objects.exists())
        self.assertTrue(self.cart.items.exists())

    def test_invalid_payment(self):
        for value in (None, "online", "forged"):
            data = dict(self.payload)
            if value is None: data.pop("payment_method")
            else: data["payment_method"] = value
            self.assertEqual(self.client.post(reverse("checkout"), data).status_code, 200)
            self.assertFalse(Order.objects.exists())

    def test_invalid_delivery_details(self):
        for field, value in [("phone", "bad"), ("phone", "1" * 21), ("address", " ")]:
            self.client.post(reverse("checkout"), {**self.payload, field: value})
            self.assertFalse(Order.objects.exists())

    def test_availability_rechecked(self):
        for obj, field in [(self.food, "is_available"), (self.category, "is_active"), (self.restaurant, "is_open"), (self.restaurant, "is_approved")]:
            setattr(obj, field, False); obj.save()
            self.client.post(reverse("checkout"), self.payload)
            self.assertFalse(Order.objects.exists())
            setattr(obj, field, True); obj.save()

    def test_minimum(self):
        self.restaurant.minimum_order = 1000; self.restaurant.save()
        self.client.post(reverse("checkout"), self.payload)
        self.assertFalse(Order.objects.exists())

    def test_mutations_reject_get(self):
        for name, args in [("increase_cart_item", [self.item.pk]), ("decrease_cart_item", [self.item.pk]), ("remove_cart_item", [self.item.pk]), ("add_to_cart", [self.food.pk]), ("logout", [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 405)
        self.item.refresh_from_db(); self.assertEqual(self.item.quantity, 2)

    def test_csrf(self):
        client = Client(enforce_csrf_checks=True); client.force_login(self.customer)
        self.assertEqual(client.post(reverse("checkout"), self.payload).status_code, 403)
        self.assertEqual(client.post(reverse("add_to_cart", args=[self.food.pk])).status_code, 403)

    def test_cart_ownership(self):
        self.client.force_login(self.other); Cart.objects.create(user=self.other)
        self.assertEqual(self.client.post(reverse("remove_cart_item", args=[self.item.pk])).status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=self.item.pk).exists())

    def test_order_ownership(self):
        order = self.place(); self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("order_detail", args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("track_order"), {"order_id": order.pk}).status_code, 404)

    def test_admin_permissions(self):
        for role in ("customer", "admin"):
            self.customer.role = role; self.customer.save()
            for name in ("admin_dashboard", "admin_users", "admin_restaurants", "admin_orders", "admin_analytics"):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.customer.is_staff = True; self.customer.save()
        self.assertEqual(self.client.get(reverse("admin_users")).status_code, 403)

    def test_admin_pages(self):
        self.place(); self.client.force_login(self.admin)
        for name in ("admin_dashboard", "admin_users", "admin_restaurants", "admin_orders", "admin_analytics"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertContains(self.client.get(reverse("admin_restaurants")), "Test Kitchen")

    def test_admin_controls(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("admin_users"), {"id": self.admin.pk})
        self.admin.refresh_from_db(); self.assertTrue(self.admin.is_active)
        self.client.post(reverse("admin_users"), {"id": self.other.pk})
        self.other.refresh_from_db(); self.assertFalse(self.other.is_active)
        self.client.post(reverse("admin_restaurants"), {"id": self.restaurant.pk})
        self.restaurant.refresh_from_db(); self.assertFalse(self.restaurant.is_approved)

    def test_restaurant_ownership(self):
        order = self.place()
        for name, args in [("edit_food", [self.food.pk]), ("delete_food", [self.food.pk]), ("restaurant_order_detail", [order.pk])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 404)
        self.assertEqual(self.client.post(reverse("update_order_status", args=[order.pk]), {"status": "confirmed"}).status_code, 404)

    def test_lifecycle(self):
        order = self.place(); self.client.force_login(self.owner)
        for status in ("confirmed", "preparing", "out_for_delivery", "delivered"):
            self.assertEqual(self.client.post(reverse("update_order_status", args=[order.pk]), {"status": status}).status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, "delivered")
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(order.payment.status, "paid")
        self.assertEqual(EmailNotification.objects.count(), 5)

    def test_transition_rules(self):
        order = self.place()
        with self.assertRaises(ValidationError): transition_order(order.pk, "delivered")
        transition_order(order.pk, "cancelled")
        with self.assertRaises(ValidationError): transition_order(order.pk, "confirmed")
        order.refresh_from_db()
        self.assertEqual(order.payment_status, "failed")
        self.assertEqual(order.payment.status, "failed")

    def test_online_not_falsely_paid(self):
        order = self.place()
        Payment.objects.filter(order=order).update(payment_method="online")
        Order.objects.filter(pk=order.pk).update(status="out_for_delivery")
        transition_order(order.pk, "delivered"); order.refresh_from_db()
        self.assertEqual(order.payment.status, "pending")
        self.assertEqual(order.payment_status, "pending")

    def test_paid_cancellation_preserves_payment(self):
        order = self.place()
        Payment.objects.filter(order=order).update(status="paid", payment_method="online")
        Order.objects.filter(pk=order.pk).update(payment_status="paid")
        transition_order(order.pk, "cancelled"); order.refresh_from_db()
        self.assertEqual(order.payment_status, "paid")
        self.assertEqual(order.payment.status, "paid")

    def test_food_validation(self):
        restaurant = Restaurant.objects.create(owner=self.owner, name="Other", address="Lahore", phone="12345678", email="other@kitchen.example", opening_time="09:00", closing_time="23:00")
        category = Category.objects.create(restaurant=restaurant, name="Other")
        form = FoodForm({"restaurant": self.restaurant.pk, "category": category.pk, "name": "Bad", "price": "-1", "discount_price": "2", "preparation_time": 20}, user=self.owner)
        self.assertFalse(form.is_valid())
        for field in ("category", "price", "discount_price"): self.assertIn(field, form.errors)

    def test_duplicate_category(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse("add_category"), {"restaurant": self.restaurant.pk, "name": "Burgers"}).status_code, 302)
        self.assertEqual(Category.objects.count(), 1)

    def test_notification_retry(self):
        self.place()
        with patch("django.core.mail.send_mail", side_effect=OSError("offline")): call_command("send_notifications")
        item = EmailNotification.objects.get()
        self.assertIsNone(item.sent_at); self.assertEqual(item.attempts, 1)
        call_command("send_notifications"); item.refresh_from_db()
        self.assertIsNotNone(item.sent_at); self.assertEqual(len(mail.outbox), 1)
        call_command("send_notifications"); self.assertEqual(len(mail.outbox), 1)

    def test_password_reset(self):
        self.assertEqual(self.client.post(reverse("password_reset"), {"email": self.customer.email}).status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        token = default_token_generator.make_token(self.customer)
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        response = self.client.get(reverse("password_reset_confirm", args=[uid, token]))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(response.url, {"new_password1": "ChangedSecurePassword!883", "new_password2": "ChangedSecurePassword!883"})
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("ChangedSecurePassword!883"))
        self.assertFalse(default_token_generator.check_token(self.customer, token))

    def test_pages(self):
        for name in ("home", "restaurants", "cart", "checkout", "orders", "track_order", "profile", "edit_profile", "change_password", "password_reset"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for name, pk in [("restaurant_detail", self.restaurant.pk), ("food_detail", self.food.pk)]:
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 200, name)

    def test_restaurant_pages(self):
        self.client.force_login(self.owner)
        for name in ("restaurant_dashboard", "restaurant_menu", "add_food", "category_management", "add_category", "restaurant_settings", "restaurant_orders", "restaurant_analytics"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_search_visibility(self):
        self.assertContains(self.client.get(reverse("restaurants"), {"q": "Zinger"}), self.restaurant.name)
        self.restaurant.is_approved = False; self.restaurant.save()
        self.assertEqual(self.client.get(reverse("food_detail", args=[self.food.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("add_to_cart", args=[self.food.pk])).status_code, 404)

    def test_currency_snapshot(self):
        order = self.place()
        with override_settings(COMMERCE_CURRENCY="USD"):
            self.assertContains(self.client.get(reverse("order_detail", args=[order.pk])), "PKR")


    def test_malformed_filters(self):
        self.client.force_login(self.owner)
        for name in ("restaurant_dashboard", "restaurant_orders", "restaurant_settings", "restaurant_analytics"):
            self.assertEqual(self.client.get(reverse(name), {"restaurant": "bad"}).status_code, 404)
        for date in ("bad", "2026-99-99"):
            self.assertEqual(self.client.get(reverse("restaurant_orders"), {"date": date}).status_code, 200)
        self.assertEqual(self.client.get(reverse("track_order"), {"order_id": "bad"}).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("admin_users"), {"id": "bad"}).status_code, 404)

    def test_profile_duplicate_email(self):
        response = self.client.post(reverse("edit_profile"), {"email": self.other.email.upper(), "first_name": "Name", "last_name": ""})
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "customer@example.com")

    def test_login_destination(self):
        self.client.logout()
        data = {"username": "customer", "password": "SecurePassword!891", "next": "/cart/"}
        self.assertRedirects(self.client.post(reverse("login"), data), "/cart/", fetch_redirect_response=False)
        self.client.logout(); data["next"] = "https://attacker.example/"
        self.assertRedirects(self.client.post(reverse("login"), data), "/", fetch_redirect_response=False)

    def test_upload_limit(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.validation import validate_image_upload
        large = SimpleUploadedFile("photo.jpg", b"a" * (5 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError): validate_image_upload(large)
        self.assertFalse(validate_image_upload(False))

    def test_settings_validation(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("restaurant_settings"), {"name": "Kitchen", "address": "Lahore", "phone": "03001234567", "email": "kitchen@example.com", "opening_time": "09:00", "closing_time": "23:00", "delivery_fee": "-1", "minimum_order": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.delivery_fee, Decimal("100"))


    def test_menu_create_edit_and_archive(self):
        self.client.force_login(self.owner)
        data = {"restaurant": self.restaurant.pk, "category": self.category.pk, "name": "New Burger", "price": "600", "discount_price": "500", "preparation_time": "20", "is_available": "on"}
        self.assertEqual(self.client.post(reverse("add_food"), data).status_code, 302)
        food = Food.objects.get(name="New Burger")
        data.update(name="Updated Burger", price="650")
        self.assertEqual(self.client.post(reverse("edit_food", args=[food.pk]), data).status_code, 302)
        food.refresh_from_db(); self.assertEqual(food.price, Decimal("650"))
        self.assertEqual(self.client.post(reverse("delete_food", args=[food.pk])).status_code, 302)
        food.refresh_from_db(); self.assertFalse(food.is_available)

    def test_category_create_and_settings_save(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse("add_category"), {"restaurant": self.restaurant.pk, "name": "Desserts"}).status_code, 302)
        self.assertTrue(Category.objects.filter(name="Desserts", restaurant=self.restaurant).exists())
        data = {"name": "Updated Kitchen", "address": "Lahore", "phone": "03001234567", "email": "kitchen@example.com", "opening_time": "09:00", "closing_time": "23:00", "delivery_fee": "150", "minimum_order": "500", "is_open": "on"}
        self.assertEqual(self.client.post(reverse("restaurant_settings"), data).status_code, 302)
        self.restaurant.refresh_from_db(); self.assertEqual(self.restaurant.delivery_fee, Decimal("150"))
        self.assertTrue(self.restaurant.is_approved)

    def test_cart_quantity_operations(self):
        self.client.post(reverse("increase_cart_item", args=[self.item.pk]))
        self.item.refresh_from_db(); self.assertEqual(self.item.quantity, 3)
        self.client.post(reverse("decrease_cart_item", args=[self.item.pk]))
        self.item.refresh_from_db(); self.assertEqual(self.item.quantity, 2)
        self.client.post(reverse("remove_cart_item", args=[self.item.pk]))
        self.assertFalse(self.cart.items.exists())
        self.client.post(reverse("add_to_cart", args=[self.food.pk]))
        self.assertEqual(self.cart.items.get().quantity, 1)

    def test_admin_order_updates_and_search(self):
        order = self.place(); self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("admin_orders"), {"id": order.pk, "status": "confirmed"}).status_code, 302)
        order.refresh_from_db(); self.assertEqual(order.status, "confirmed")
        self.assertContains(self.client.get(reverse("admin_orders"), {"q": "customer", "status": "confirmed"}), "Test Kitchen")
        self.assertNotContains(self.client.get(reverse("admin_orders"), {"q": "nonexistent"}), "Test Kitchen")

    def test_django_financial_admin_is_read_only(self):
        order = self.place(); self.client.force_login(self.admin)
        response = self.client.post(f"/admin/core/payment/{order.payment.pk}/change/", {"status": "paid", "amount": "1", "payment_method": "online"})
        self.assertIn(response.status_code, (200, 302))
        order.payment.refresh_from_db()
        self.assertEqual(Payment.objects.get(order=order).status, "pending")
        self.assertEqual(Payment.objects.get(order=order).amount, Decimal("900"))


    def test_home_shows_uploaded_images_and_hero(self):
        self.food.image = "foods/zinger.jpg"
        self.food.save(update_fields=["image"])
        self.restaurant.cover_image = "restaurants/covers/cafe.jpg"
        self.restaurant.save(update_fields=["cover_image"])
        response = self.client.get(reverse("home"))
        self.assertContains(response, "/media/foods/zinger.jpg")
        self.assertContains(response, "/media/restaurants/covers/cafe.jpg")
        self.assertContains(response, "/static/images/hero/hero-pizza.png")
        self.assertContains(response, "/static/css/home.css")
        self.assertContains(response, "PKR")

    def test_home_closed_restaurant_menu_is_browsable(self):
        self.restaurant.is_open = False
        self.restaurant.save(update_fields=["is_open"])
        response = self.client.get(reverse("home"))
        self.assertContains(response, self.food.name)
        self.assertContains(response, "Closed now")
        self.assertNotContains(response, 'aria-label="Add Zinger to cart"')
