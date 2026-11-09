from core.validation import positive_id
from django.utils.dateparse import parse_date
from decimal import Decimal
from datetime import timedelta

from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils import timezone

from core.models import (
    Restaurant,
    Order,
    OrderItem,
    Payment,
    Food,
    Category,
)

from .forms import FoodForm


# =========================================================
# RESTAURANT DASHBOARD
# =========================================================

@login_required
def dashboard(request):

    restaurants = Restaurant.objects.filter(
        owner=request.user
    ).order_by("name")

    restaurant_id = request.GET.get("restaurant")

    if restaurant_id:

        restaurant = get_object_or_404(
            Restaurant,
            id=positive_id(restaurant_id),
            owner=request.user
        )

    else:

        restaurant = restaurants.first()

    # No restaurant
    if not restaurant:

        return render(
            request,
            "restaurant_dashboard/dashboard.html",
            {
                "restaurants": restaurants,
                "restaurant": None,

                "total_foods": 0,
                "available_foods": 0,

                "total_orders": 0,
                "pending_orders": 0,
                "confirmed_orders": 0,
                "preparing_orders": 0,
                "out_for_delivery_orders": 0,
                "delivered_orders": 0,
                "cancelled_orders": 0,

                "total_revenue": Decimal("0.00"),

                "recent_orders": [],
            }
        )

    # =====================================================
    # FOODS
    # =====================================================

    foods = Food.objects.filter(
        restaurant=restaurant
    )

    total_foods = foods.count()

    available_foods = foods.filter(
        is_available=True
    ).count()

    # =====================================================
    # ORDERS
    # =====================================================

    orders = Order.objects.filter(
        restaurant=restaurant
    ).select_related(
        "restaurant",
        "user"
    ).order_by(
        "-created_at"
    )

    total_orders = orders.count()

    pending_orders = orders.filter(
        status=Order.PENDING
    ).count()

    confirmed_orders = orders.filter(
        status=Order.CONFIRMED
    ).count()

    preparing_orders = orders.filter(
        status=Order.PREPARING
    ).count()

    out_for_delivery_orders = orders.filter(
        status=Order.OUT_FOR_DELIVERY
    ).count()

    delivered_orders = orders.filter(
        status=Order.DELIVERED
    ).count()

    cancelled_orders = orders.filter(
        status=Order.CANCELLED
    ).count()

    # =====================================================
    # REVENUE
    # =====================================================

    delivered_order_list = orders.filter(
        status=Order.DELIVERED
    )

    total_revenue = sum(
        (
            order.total
            for order in delivered_order_list
            if order.total
        ),
        Decimal("0.00")
    )

    # =====================================================
    # RECENT ORDERS
    # =====================================================

    recent_orders = orders[:5]

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "restaurants": restaurants,

        "restaurant": restaurant,

        "total_foods": total_foods,

        "available_foods": available_foods,

        "total_orders": total_orders,

        "pending_orders": pending_orders,

        "confirmed_orders": confirmed_orders,

        "preparing_orders": preparing_orders,

        "out_for_delivery_orders":
            out_for_delivery_orders,

        "delivered_orders":
            delivered_orders,

        "cancelled_orders":
            cancelled_orders,

        "total_revenue":
            total_revenue,

        "recent_orders":
            recent_orders,
    }

    return render(
        request,
        "restaurant_dashboard/dashboard.html",
        context
    )


# =========================================================
# MENU MANAGEMENT
# =========================================================

@login_required
def menu_management(request):

    foods = Food.objects.filter(
        restaurant__owner=request.user
    ).select_related(
        "restaurant",
        "category"
    ).order_by(
        "restaurant__name",
        "name"
    )

    context = {
        "foods": foods
    }

    return render(
        request,
        "restaurant_dashboard/menu.html",
        context
    )


# =========================================================
# ADD FOOD
# =========================================================

@login_required
def add_food(request):

    if request.method == "POST":

        form = FoodForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():

            food = form.save()

            messages.success(
                request,
                f"{food.name} was added to your menu."
            )

            return redirect(
                "restaurant_menu"
            )

    else:

        form = FoodForm(
            user=request.user
        )

    return render(
        request,
        "restaurant_dashboard/add_food.html",
        {
            "form": form
        }
    )


# =========================================================
# EDIT FOOD
# =========================================================

@login_required
def edit_food(request, id):

    food = get_object_or_404(
        Food,
        id=id,
        restaurant__owner=request.user
    )

    if request.method == "POST":

        form = FoodForm(
            request.POST,
            request.FILES,
            instance=food,
            user=request.user
        )

        if form.is_valid():

            food = form.save()

            messages.success(
                request,
                f"{food.name} was updated successfully."
            )

            return redirect(
                "restaurant_menu"
            )

    else:

        form = FoodForm(
            instance=food,
            user=request.user
        )

    return render(
        request,
        "restaurant_dashboard/edit_food.html",
        {
            "form": form,
            "food": food
        }
    )


# =========================================================
# DELETE FOOD
# =========================================================

@login_required
def delete_food(request, id):

    food = get_object_or_404(
        Food,
        id=id,
        restaurant__owner=request.user
    )

    if request.method == "POST":

        food.is_available = False

        food.save(
            update_fields=[
                "is_available"
            ]
        )

        messages.success(
            request,
            f"{food.name} was removed from your menu."
        )

        return redirect(
            "restaurant_menu"
        )

    return render(
        request,
        "restaurant_dashboard/delete_food.html",
        {
            "food": food
        }
    )


# =========================================================
# RESTAURANT ORDERS
# =========================================================

@login_required
def restaurant_orders(request):

    restaurants = Restaurant.objects.filter(
        owner=request.user
    ).order_by("name")

    restaurant_id = request.GET.get(
        "restaurant"
    )

    if restaurant_id:

        restaurant = get_object_or_404(
            Restaurant,
            id=positive_id(restaurant_id),
            owner=request.user
        )

    else:

        restaurant = restaurants.first()

    # =====================================================
    # NO RESTAURANT
    # =====================================================

    if not restaurant:

        return render(
            request,
            "restaurant_dashboard/orders.html",
            {
                "restaurant": None,

                "restaurants": restaurants,

                "orders": [],

                "total_orders": 0,

                "pending_orders": 0,

                "preparing_orders": 0,

                "delivered_orders": 0,

                "cancelled_orders": 0,

                "search_query": "",

                "selected_status": "",

                "selected_date": "",
            }
        )

    # =====================================================
    # ALL ORDERS
    # =====================================================

    all_orders = Order.objects.filter(
        restaurant=restaurant
    ).select_related(
        "user",
        "restaurant"
    ).prefetch_related(
        "items"
    ).order_by(
        "-created_at"
    )

    # =====================================================
    # STATISTICS
    # =====================================================

    total_orders = all_orders.count()

    pending_orders = all_orders.filter(
        status=Order.PENDING
    ).count()

    preparing_orders = all_orders.filter(
        status__in=[
            Order.CONFIRMED,
            Order.PREPARING,
            Order.OUT_FOR_DELIVERY,
        ]
    ).count()

    delivered_orders = all_orders.filter(
        status=Order.DELIVERED
    ).count()

    cancelled_orders = all_orders.filter(
        status=Order.CANCELLED
    ).count()

    # =====================================================
    # FILTERS
    # =====================================================

    orders = all_orders

    search_query = request.GET.get(
        "search",
        ""
    ).strip()

    selected_status = request.GET.get(
        "status",
        ""
    ).strip()

    selected_date = request.GET.get(
        "date",
        ""
    ).strip()

    # =====================================================
    # CUSTOMER SEARCH
    # =====================================================

    if search_query:

        orders = orders.filter(
            Q(
                user__username__icontains=search_query
            )
            |
            Q(
                user__first_name__icontains=search_query
            )
            |
            Q(
                user__last_name__icontains=search_query
            )
        )

    # =====================================================
    # STATUS FILTER
    # =====================================================

    valid_statuses = [

        Order.PENDING,

        Order.CONFIRMED,

        Order.PREPARING,

        Order.OUT_FOR_DELIVERY,

        Order.DELIVERED,

        Order.CANCELLED,
    ]

    if selected_status in valid_statuses:

        orders = orders.filter(
            status=selected_status
        )

    # =====================================================
    # DATE FILTER
    # =====================================================

    if selected_date:
        try:
            valid_date = parse_date(selected_date)
        except ValueError:
            valid_date = None
        if valid_date is None:
            messages.error(request, "Enter a valid date in YYYY-MM-DD format.")
            selected_date = ""

    if selected_date:
        orders = orders.filter(
            created_at__date=selected_date
        )

    # =====================================================
    # AVAILABLE STATUS CHANGES
    # =====================================================

    for order in orders:

        if order.status == Order.PENDING:

            order.available_statuses = [

                (
                    Order.CONFIRMED,
                    "Confirmed"
                ),

                (
                    Order.CANCELLED,
                    "Cancelled"
                ),
            ]

        elif order.status == Order.CONFIRMED:

            order.available_statuses = [

                (
                    Order.PREPARING,
                    "Preparing"
                ),

                (
                    Order.CANCELLED,
                    "Cancelled"
                ),
            ]

        elif order.status == Order.PREPARING:

            order.available_statuses = [

                (
                    Order.OUT_FOR_DELIVERY,
                    "Out for Delivery"
                ),

                (
                    Order.CANCELLED,
                    "Cancelled"
                ),
            ]

        elif order.status == Order.OUT_FOR_DELIVERY:

            order.available_statuses = [

                (
                    Order.DELIVERED,
                    "Delivered"
                ),
            ]

        else:

            order.available_statuses = []

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "restaurant":
            restaurant,

        "restaurants":
            restaurants,

        "orders":
            orders,

        "selected_status":
            selected_status,

        "search_query":
            search_query,

        "selected_date":
            selected_date,

        "total_orders":
            total_orders,

        "pending_orders":
            pending_orders,

        "preparing_orders":
            preparing_orders,

        "delivered_orders":
            delivered_orders,

        "cancelled_orders":
            cancelled_orders,
    }

    return render(
        request,
        "restaurant_dashboard/orders.html",
        context
    )


# =========================================================
# UPDATE ORDER STATUS + PAYMENT
# =========================================================

@login_required
@require_POST
def update_order_status(request, id):

    from core.services import transition_order
    from django.core.exceptions import ValidationError
    order = get_object_or_404(Order, id=id, restaurant__owner=request.user)
    try:
        transition_order(order.pk, request.POST.get("status"), owner=request.user)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, f"Order #{order.pk} updated.")
    return redirect(f"/restaurant/dashboard/orders/?restaurant={order.restaurant_id}")


# =========================================================
# RESTAURANT ANALYTICS
# =========================================================

@login_required
def restaurant_analytics(request):

    restaurants = Restaurant.objects.filter(
        owner=request.user
    )

    restaurant_id = request.GET.get(
        "restaurant"
    )

    if restaurant_id:

        restaurant = get_object_or_404(
            Restaurant,
            id=positive_id(restaurant_id),
            owner=request.user
        )

    else:

        restaurant = restaurants.first()

    # =====================================================
    # NO RESTAURANT
    # =====================================================

    if not restaurant:

        return render(
            request,
            "restaurant_dashboard/analytics.html",
            {
                "restaurants": restaurants,
                "restaurant": None,
            }
        )

    # =====================================================
    # ORDERS
    # =====================================================

    orders = Order.objects.filter(
        restaurant=restaurant
    ).prefetch_related(
        "items"
    ).order_by(
        "-created_at"
    )

    # =====================================================
    # BASIC STATISTICS
    # =====================================================

    total_orders = orders.count()

    delivered_orders = orders.filter(
        status=Order.DELIVERED
    ).count()

    cancelled_orders = orders.filter(
        status=Order.CANCELLED
    ).count()

    pending_orders = orders.filter(
        status=Order.PENDING
    ).count()

    confirmed_orders = orders.filter(
        status=Order.CONFIRMED
    ).count()

    preparing_orders = orders.filter(
        status=Order.PREPARING
    ).count()

    out_for_delivery_orders = orders.filter(
        status=Order.OUT_FOR_DELIVERY
    ).count()

    # =====================================================
    # REVENUE
    # =====================================================

    delivered_order_list = orders.filter(
        status=Order.DELIVERED
    )

    total_revenue = Decimal("0.00")

    for order in delivered_order_list:

        if order.total:

            total_revenue += order.total

    # =====================================================
    # AVERAGE ORDER VALUE
    # =====================================================

    if delivered_orders > 0:

        average_order_value = (
            total_revenue /
            delivered_orders
        )

    else:

        average_order_value = Decimal("0.00")

    # =====================================================
    # LAST 7 DAYS
    # =====================================================

    today = timezone.localdate()

    revenue_labels = []

    revenue_values = []

    order_labels = []

    order_values = []

    for number in range(
        6,
        -1,
        -1
    ):

        current_date = today - timedelta(
            days=number
        )

        daily_orders = orders.filter(
            created_at__date=current_date
        )

        daily_revenue = Decimal("0.00")

        for order in daily_orders:

            if order.status == Order.DELIVERED:

                if order.total:

                    daily_revenue += order.total

        revenue_labels.append(
            current_date.strftime(
                "%d %b"
            )
        )

        revenue_values.append(
            float(daily_revenue)
        )

        order_labels.append(
            current_date.strftime(
                "%d %b"
            )
        )

        order_values.append(
            daily_orders.count()
        )

    # =====================================================
    # POPULAR FOOD ITEMS
    # =====================================================

    food_sales = {}

    for order in delivered_order_list:

        for item in order.items.all():

            food_name = item.food_name

            if food_name not in food_sales:

                food_sales[food_name] = 0

            food_sales[food_name] += (
                item.quantity
            )

    popular_foods = sorted(
        food_sales.items(),
        key=lambda item: item[1],
        reverse=True
    )

    popular_foods = popular_foods[:5]

    popular_food_data = []

    popular_food_labels = []

    popular_food_values = []

    for food_name, quantity in popular_foods:

        popular_food_data.append(
            {
                "name": food_name,
                "quantity": quantity
            }
        )

        popular_food_labels.append(
            food_name
        )

        popular_food_values.append(
            quantity
        )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "restaurants":
            restaurants,

        "restaurant":
            restaurant,

        "total_orders":
            total_orders,

        "total_revenue":
            total_revenue,

        "average_order_value":
            average_order_value,

        "pending_orders":
            pending_orders,

        "confirmed_orders":
            confirmed_orders,

        "preparing_orders":
            preparing_orders,

        "out_for_delivery_orders":
            out_for_delivery_orders,

        "delivered_orders":
            delivered_orders,

        "cancelled_orders":
            cancelled_orders,

        "revenue_labels":
            revenue_labels,

        "revenue_values":
            revenue_values,

        "order_labels":
            order_labels,

        "order_values":
            order_values,

        "popular_foods":
            popular_food_data,

        "popular_food_labels":
            popular_food_labels,

        "popular_food_values":
            popular_food_values,
    }

    return render(
        request,
        "restaurant_dashboard/analytics.html",
        context
    )


# =========================================================
# CATEGORY MANAGEMENT
# =========================================================

@login_required
def category_management(request):

    restaurants = Restaurant.objects.filter(
        owner=request.user
    )

    categories = Category.objects.filter(
        restaurant__owner=request.user
    ).prefetch_related(
        "foods"
    ).order_by(
        "restaurant__name",
        "name"
    )

    return render(
        request,
        "restaurant_dashboard/categories.html",
        {
            "restaurants": restaurants,
            "categories": categories,
        }
    )


# =========================================================
# ADD CATEGORY
# =========================================================

@login_required
def add_category(request):

    restaurants = Restaurant.objects.filter(
        owner=request.user
    )

    if request.method == "POST":

        restaurant_id = request.POST.get(
            "restaurant"
        )

        name = request.POST.get("name", "").strip()

        description = request.POST.get(
            "description",
            ""
        )

        restaurant = get_object_or_404(
            Restaurant,
            id=positive_id(restaurant_id),
            owner=request.user
        )

        if not name:

            messages.error(
                request,
                "Category name is required."
            )

            return redirect(
                "add_category"
            )

        if len(name) > 100 or Category.objects.filter(restaurant=restaurant, name__iexact=name).exists():
            messages.error(request, "Choose a unique category name of at most 100 characters.")
            return redirect("add_category")
        Category.objects.create(restaurant=restaurant, name=name, description=description)

        messages.success(
            request,
            f"{name} category was created successfully."
        )

        return redirect(
            "category_management"
        )

    return render(
        request,
        "restaurant_dashboard/add_category.html",
        {
            "restaurants":
                restaurants
        }
    )


# =========================================================
# RESTAURANT SETTINGS
# =========================================================

@login_required
def restaurant_settings(request):

    restaurants = Restaurant.objects.filter(
        owner=request.user
    ).order_by(
        "name"
    )

    restaurant_id = request.GET.get(
        "restaurant"
    )

    if restaurant_id:

        restaurant = get_object_or_404(
            Restaurant,
            id=positive_id(restaurant_id),
            owner=request.user
        )

    else:

        restaurant = restaurants.first()

    # =====================================================
    # NO RESTAURANT
    # =====================================================

    if not restaurant:

        return render(
            request,
            "restaurant_dashboard/settings.html",
            {
                "restaurant": None,
                "restaurants": restaurants,
            }
        )

    # =====================================================
    # UPDATE SETTINGS
    # =====================================================

    if request.method == "POST":

        from .forms import RestaurantSettingsForm
        form = RestaurantSettingsForm(request.POST, request.FILES, instance=restaurant)
        if not form.is_valid():
            messages.error(request, " ".join(str(e) for errors in form.errors.values() for e in errors))
            return render(request, "restaurant_dashboard/settings.html", {"restaurant": restaurant, "restaurants": restaurants, "form": form})
        form.save()

        messages.success(
            request,
            "Restaurant settings updated successfully."
        )

        return redirect(
            f"/restaurant/settings/?restaurant={restaurant.id}"
        )

    return render(
        request,
        "restaurant_dashboard/settings.html",
        {
            "restaurant":
                restaurant,

            "restaurants":
                restaurants,
        }
    )


# =========================================================
# RESTAURANT ORDER DETAIL
# =========================================================

@login_required
def restaurant_order_detail(request, id):

    order = get_object_or_404(

        Order.objects.select_related(
            "user",
            "restaurant"
        ).prefetch_related(
            "items__food"
        ),

        id=id,

        restaurant__owner=request.user
    )

    return render(
        request,
        "restaurant_dashboard/order_detail.html",
        {
            "order": order
        }
    )