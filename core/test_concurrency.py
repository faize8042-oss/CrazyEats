from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.test import TransactionTestCase, Client
from django.db import connection, connections
from core.models import User, Restaurant, Category, Food, Cart, CartItem, Order, Payment

@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locking; run the supplied CI job.")
class CheckoutConcurrencyTests(TransactionTestCase):
    def test_simultaneous_submit_creates_one_order(self):
        user = User.objects.create_user("concurrent", "concurrent@example.com", "SecurePassword!891")
        owner = User.objects.create_user("concurrent-owner", "owner@example.com", "SecurePassword!891")
        restaurant = Restaurant.objects.create(owner=owner, name="Kitchen", address="Lahore", phone="03000000000", email="kitchen@example.com", opening_time="09:00", closing_time="23:00", is_approved=True)
        category = Category.objects.create(restaurant=restaurant, name="Food")
        food = Food.objects.create(restaurant=restaurant, category=category, name="Rice", price=450)
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, food=food)
        clients = [Client(), Client()]
        for client in clients: client.force_login(user)
        barrier = Barrier(2)
        def submit(client):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                barrier.wait(timeout=10)
                return client.post("/checkout/", {"address": "House 12, Main Road Lahore", "phone": "03000000000", "payment_method": "cod"}).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(submit, client) for client in clients]
            self.assertEqual([future.result(timeout=20) for future in futures], [302, 302])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertFalse(cart.items.exists())
