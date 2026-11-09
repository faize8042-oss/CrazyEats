from core.validation import positive_id
from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.shortcuts import render, redirect, get_object_or_404
from core.models import User, Restaurant, Order
from core.services import transition_order, TRANSITIONS

def staff_only(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped

def permitted(request, permission):
    if not request.user.has_perm(permission):
        raise PermissionDenied

def summary():
    return {"total_users": User.objects.count(), "total_restaurants": Restaurant.objects.count(), "total_orders": Order.objects.count(), "pending_orders": Order.objects.filter(status="pending").count(), "total_revenue": Order.objects.filter(status="delivered", payment_status="paid").aggregate(value=Sum("total"))["value"] or 0}

@staff_only
def dashboard(request):
    permitted(request, "core.view_order")
    return render(request, "admin_dashboard/dashboard.html", summary())

@staff_only
def users(request):
    permitted(request, "core.view_user")
    if request.method == "POST":
        permitted(request, "core.change_user")
        target = get_object_or_404(User, pk=positive_id(request.POST.get("id")))
        if target.pk == request.user.pk or target.is_staff or target.is_superuser:
            messages.error(request, "Staff accounts cannot be disabled here.")
        else:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            messages.success(request, "User status updated.")
        return redirect("admin_users")
    q = request.GET.get("q", "").strip()[:100]
    records = User.objects.filter(Q(username__icontains=q) | Q(email__icontains=q)).order_by("-date_joined")
    return render(request, "admin_dashboard/users.html", {"page_obj": Paginator(records, 25).get_page(request.GET.get("page")), "q": q})

@staff_only
def restaurants(request):
    permitted(request, "core.view_restaurant")
    if request.method == "POST":
        permitted(request, "core.change_restaurant")
        restaurant = get_object_or_404(Restaurant, pk=positive_id(request.POST.get("id")))
        restaurant.is_approved = not restaurant.is_approved
        restaurant.save(update_fields=["is_approved", "updated_at"])
        messages.success(request, "Restaurant approval updated.")
        return redirect("admin_restaurants")
    q = request.GET.get("q", "").strip()[:100]
    records = Restaurant.objects.filter(name__icontains=q).select_related("owner")
    return render(request, "admin_dashboard/restaurants.html", {"page_obj": Paginator(records, 25).get_page(request.GET.get("page")), "q": q})

@staff_only
def orders(request):
    permitted(request, "core.view_order")
    if request.method == "POST":
        permitted(request, "core.change_order")
        order = get_object_or_404(Order, pk=positive_id(request.POST.get("id")))
        try:
            transition_order(order.pk, request.POST.get("status"))
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
        else:
            messages.success(request, "Order updated.")
        return redirect("admin_orders")
    records = Order.objects.select_related("user", "restaurant")
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()[:100]
    if status in dict(Order.STATUS_CHOICES):
        records = records.filter(status=status)
    if q:
        records = records.filter(Q(user__username__icontains=q) | Q(restaurant__name__icontains=q))
    page = Paginator(records, 25).get_page(request.GET.get("page"))
    for order in page:
        order.available_statuses = [(s, dict(Order.STATUS_CHOICES)[s]) for s in TRANSITIONS.get(order.status, [])]
    return render(request, "admin_dashboard/orders.html", {"page_obj": page, "q": q, "status": status, "statuses": Order.STATUS_CHOICES})

@staff_only
def analytics(request):
    permitted(request, "core.view_order")
    context = summary()
    context["by_status"] = Order.objects.values("status").annotate(count=Count("pk")).order_by("status")
    return render(request, "admin_dashboard/analytics.html", context)
