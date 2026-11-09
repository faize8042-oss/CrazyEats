from django.shortcuts import render
from core.models import Restaurant, Food

def home(request):
    return render(request, "home/index.html", {
        "restaurants": Restaurant.objects.filter(is_approved=True)[:6],
        "foods": Food.objects.filter(is_available=True, category__is_active=True, restaurant__is_approved=True).select_related("restaurant").order_by("-is_today_special", "-is_featured", "-created_at")[:8],
    })
