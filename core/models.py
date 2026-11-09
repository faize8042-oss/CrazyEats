from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower, Trim
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    CUSTOMER = "customer"
    RESTAURANT = "restaurant"
    ADMIN = "admin"

    ROLE_CHOICES = [

        (CUSTOMER, "Customer"),
        (RESTAURANT, "Restaurant"),
        (ADMIN, "Admin"),

    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=CUSTOMER
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True
    )

    class Meta(AbstractUser.Meta):
        constraints = [models.UniqueConstraint(Lower(Trim("email")), condition=~models.Q(email=""), name="unique_recovery_email")]

    def __str__(self):

        return self.username


class Restaurant(models.Model):

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="restaurants"
    )

    name = models.CharField(
        max_length=200
    )

    logo = models.ImageField(
        upload_to="restaurants/logos/",
        blank=True,
        null=True
    )

    cover_image = models.ImageField(
        upload_to="restaurants/covers/",
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True
    )

    address = models.TextField()

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField()

    opening_time = models.TimeField()

    closing_time = models.TimeField()

    delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    minimum_order = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    is_open = models.BooleanField(
        default=True
    )

    is_approved = models.BooleanField(
        default=False
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ["name"]

    def clean(self):
        super().clean()
        errors = {}
        for field in ("delivery_fee", "minimum_order"):
            value = getattr(self, field)
            if value is not None and value < 0:
                errors[field] = "Amount cannot be negative."
        if errors:
            raise ValidationError(errors)

    def __str__(self):

        return self.name

class Category(models.Model):

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="categories"
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="categories/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["name"]

        unique_together = ("restaurant", "name")

    def __str__(self):

        return f"{self.restaurant.name} - {self.name}"

class Food(models.Model):

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="foods"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="foods"
    )

    name = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="foods/",
        blank=True,
        null=True
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    discount_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )

    preparation_time = models.PositiveIntegerField(
        default=20,
        help_text="Preparation time in minutes"
    )

    calories = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    is_available = models.BooleanField(
        default=True
    )

    is_featured = models.BooleanField(
        default=False
    )

    is_today_special = models.BooleanField(
        default=False
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = ["name"]

    def clean(self):
        super().clean()
        errors = {}
        if self.price is not None and self.price <= 0:
            errors["price"] = "Price must be positive."
        if self.discount_price is not None and (self.discount_price <= 0 or (self.price is not None and self.discount_price >= self.price)):
            errors["discount_price"] = "Discount price must be positive and lower than regular price."
        if self.category_id and self.restaurant_id and self.category.restaurant_id != self.restaurant_id:
            errors["category"] = "Category must belong to this restaurant."
        if errors:
            raise ValidationError(errors)

    def __str__(self):

        return self.name

class Cart(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return f"{self.user.username}'s Cart"

    @property
    def total_items(self):

        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):

        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    food = models.ForeignKey(
        Food,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        unique_together = ("cart", "food")

    @property
    def subtotal(self):

        if self.food.discount_price is not None:

            return self.food.discount_price * self.quantity

        return self.food.price * self.quantity

    def __str__(self):

        return f"{self.food.name} x {self.quantity}"

class Order(models.Model):

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (PREPARING, "Preparing"),
        (OUT_FOR_DELIVERY, "Out for Delivery"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
    ]

    PAYMENT_PENDING = "pending"
    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, "Pending"),
        (PAYMENT_PAID, "Paid"),
        (PAYMENT_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING
    )

    currency = models.CharField(max_length=3, default="PKR")

    delivery_address = models.TextField()

    delivery_phone = models.CharField(
        max_length=20
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    food = models.ForeignKey(
        Food,
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    food_name = models.CharField(
        max_length=200
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.food_name} x {self.quantity}"

class Payment(models.Model):

    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("online", "Online Payment"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="cod"
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending"
    )

    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Payment #{self.id} - Order #{self.order.id}"


class EmailNotification(models.Model):
    event_key = models.CharField(max_length=150, unique=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]


class RequestQuota(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
