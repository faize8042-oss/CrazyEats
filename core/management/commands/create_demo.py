import os
from datetime import time
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from core.models import User, Restaurant, Category, Food

class Command(BaseCommand):
    help = "Create synthetic demo accounts and catalog in an isolated development/staging database."
    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not settings.DEMO_MODE:
            raise CommandError("Demo setup requires DEBUG or explicit DEMO_MODE=true on isolated staging.")
        password = os.environ.get("CRAZYEATS_DEMO_PASSWORD", "")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError("Set CRAZYEATS_DEMO_PASSWORD to a strong password: " + "; ".join(exc.messages))
        group, _ = Group.objects.get_or_create(name="CrazyEats demo")
        accounts = {}
        for name, role in (("demo-customer", "customer"), ("demo-owner", "restaurant")):
            user, created = User.objects.get_or_create(username=name, defaults={"email": name + "@example.invalid", "role": role})
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                user.groups.add(group)
            elif not user.groups.filter(pk=group.pk).exists():
                raise CommandError("A non-demo account uses a reserved demo name; nothing was changed.")
            accounts[role] = user
        restaurant, _ = Restaurant.objects.get_or_create(owner=accounts["restaurant"], name="Demo Lahore Kitchen", defaults={"address": "Synthetic demo address, Lahore", "phone": "03000000000", "email": "kitchen@example.invalid", "opening_time": time(9), "closing_time": time(23), "is_approved": True, "is_open": True, "delivery_fee": 100, "minimum_order": 300})
        category, _ = Category.objects.get_or_create(restaurant=restaurant, name="Demo favourites")
        for name, price in (("Chicken Biryani", 450), ("Zinger Burger", 550), ("Vegetable Rice", 350)):
            Food.objects.get_or_create(restaurant=restaurant, category=category, name=name, defaults={"price": price, "description": "Synthetic demonstration menu item."})
        self.stdout.write("Demo ready: demo-customer and demo-owner. Existing passwords are preserved. No staff demo account is created.")
