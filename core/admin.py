from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    User,
    Restaurant,
    Category,
    Food,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Payment,
)


# ==========================================
# USER ADMIN
# ==========================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "role",
        "phone",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "email",
        "phone",
    )

    ordering = (
        "-date_joined",
    )


# ==========================================
# RESTAURANT ADMIN
# ==========================================

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "owner",
        "phone",
        "is_open",
        "is_approved",
        "rating",
        "created_at",
    )

    list_filter = (
        "is_open",
        "is_approved",
        "created_at",
    )

    search_fields = (
        "name",
        "owner__username",
        "phone",
        "email",
        "address",
    )

    list_editable = (
        "is_open",
        "is_approved",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


# ==========================================
# CATEGORY ADMIN
# ==========================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "restaurant",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "restaurant",
    )

    search_fields = (
        "name",
        "restaurant__name",
    )

    list_editable = (
        "is_active",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "restaurant",
        "name",
    )


# ==========================================
# FOOD ADMIN
# ==========================================

@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "restaurant",
        "category",
        "price",
        "discount_price",
        "is_available",
        "is_featured",
        "is_today_special",
        "rating",
    )

    list_filter = (
        "restaurant",
        "category",
        "is_available",
        "is_featured",
        "is_today_special",
    )

    search_fields = (
        "name",
        "restaurant__name",
        "category__name",
    )

    list_editable = (
        "price",
        "discount_price",
        "is_available",
        "is_featured",
        "is_today_special",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )


# ==========================================
# CART ADMIN
# ==========================================

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "created_at",
        "updated_at",
        "total_items_display",
        "total_price_display",
    )

    search_fields = (
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "total_items_display",
        "total_price_display",
    )

    def total_items_display(self, obj):
        return obj.total_items

    total_items_display.short_description = "Total Items"

    def total_price_display(self, obj):
        return obj.total_price

    total_price_display.short_description = "Total Price"


# ==========================================
# CART ITEM ADMIN
# ==========================================

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):

    list_display = (
        "cart",
        "food",
        "quantity",
        "subtotal_display",
        "created_at",
    )

    list_filter = (
        "food__restaurant",
    )

    search_fields = (
        "cart__user__username",
        "food__name",
    )

    readonly_fields = (
        "created_at",
        "subtotal_display",
    )

    def subtotal_display(self, obj):
        return obj.subtotal

    subtotal_display.short_description = "Subtotal"


# ==========================================
# ORDER ADMIN
# ==========================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "restaurant",
        "status",
        "payment_status",
        "subtotal",
        "delivery_fee",
        "discount",
        "total",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_status",
        "restaurant",
        "created_at",
    )

    search_fields = (
        "id",
        "user__username",
        "user__email",
        "restaurant__name",
        "delivery_phone",
        "delivery_address",
    )

    readonly_fields = tuple(field.name for field in Order._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    ordering = (
        "-created_at",
    )


# ==========================================
# ORDER ITEM ADMIN
# ==========================================

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "food_name",
        "price",
        "quantity",
        "subtotal",
    )

    search_fields = (
        "food_name",
        "order__user__username",
        "order__restaurant__name",
    )

    readonly_fields = (
        "food_name",
        "price",
        "subtotal",
    )

    ordering = (
        "-order",
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "amount",
        "payment_method",
        "status",
        "transaction_id",
        "created_at",
    )

    list_filter = (
        "payment_method",
        "status",
        "created_at",
    )

    search_fields = (
        "order__id",
        "order__user__username",
        "transaction_id",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

# Financial history must not be rewritten through generic administration forms.
for model, admin_class in ((Payment, PaymentAdmin), (OrderItem, OrderItemAdmin)):
    admin_class.readonly_fields = tuple(field.name for field in model._meta.fields)
    admin_class.has_add_permission = lambda self, request: False
    admin_class.has_delete_permission = lambda self, request, obj=None: False


from .models import EmailNotification

@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ("event_key", "recipient", "created_at", "sent_at", "attempts", "last_error")
    list_filter = ("sent_at",)
    search_fields = ("event_key", "recipient")
    readonly_fields = tuple(field.name for field in EmailNotification._meta.fields)
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
