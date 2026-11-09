from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm
)
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required

from .forms import EditProfileForm, RegistrationForm
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from core.models import Order, EmailNotification
from django.db import transaction, IntegrityError


# ==========================================
# REGISTER
# ==========================================

@transaction.atomic
def register_view(request):

    if request.method == "POST":

        form = RegistrationForm(request.POST)

        if form.is_valid():

            try:
                with transaction.atomic():
                    user = form.save()
            except IntegrityError:
                form.add_error(None, "This username or email was just registered. Please use another or sign in.")
                return render(request, "accounts/register.html", {"form": form})
            EmailNotification.objects.create(event_key=f"welcome:{user.pk}", recipient=user.email, subject="Welcome to CrazyEats", body="Your CrazyEats account is ready. Sign in to explore restaurants, place an order, and track delivery.")

            login(request, user)

            return redirect("home")

    else:

        form = RegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )


# ==========================================
# LOGIN
# ==========================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            login(request, user)

            destination = request.POST.get("next") or request.GET.get("next")
            if destination and url_has_allowed_host_and_scheme(destination, {request.get_host()}, require_https=request.is_secure()):
                return redirect(destination)
            return redirect("home")

    else:

        form = AuthenticationForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )


# ==========================================
# PROFILE
# ==========================================

@login_required
def profile_view(request):

    user = request.user

    user_orders = Order.objects.filter(
        user=user
    )

    total_orders = user_orders.count()

    delivered_orders = user_orders.filter(
        status=Order.DELIVERED
    ).count()

    pending_orders = user_orders.filter(
        status__in=[
            Order.PENDING,
            Order.CONFIRMED,
            Order.PREPARING,
            Order.OUT_FOR_DELIVERY,
        ]
    ).count()

    recent_orders = user_orders.select_related(
        "restaurant"
    ).order_by(
        "-created_at"
    )[:5]

    context = {

        "user": user,

        "total_orders": total_orders,

        "delivered_orders": delivered_orders,

        "pending_orders": pending_orders,

        "recent_orders": recent_orders,

    }

    return render(
        request,
        "accounts/profile.html",
        context
    )


# ==========================================
# EDIT PROFILE
# ==========================================

@login_required
def edit_profile(request):

    user = request.user

    if request.method == "POST":

        form = EditProfileForm(
            request.POST,
            instance=user
        )

        if form.is_valid():

            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError:
                form.add_error("email", "This email was just registered. Please use another.")
            else:
                return redirect("profile")

    else:

        form = EditProfileForm(
            instance=user
        )

    return render(
        request,
        "accounts/edit_profile.html",
        {
            "form": form
        }
    )


# ==========================================
# LOGOUT
# ==========================================

@require_POST
def logout_view(request):

    logout(request)

    return redirect("home")


# ==========================================
# CHANGE PASSWORD
# ==========================================

@login_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():

            user = form.save()

            # Keep the user logged in after changing password
            update_session_auth_hash(
                request,
                user
            )

            return redirect("profile")

    else:

        form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "accounts/change_password.html",
        {
            "form": form
        }
    )
