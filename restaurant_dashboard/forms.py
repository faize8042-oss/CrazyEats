from core.validation import validate_image_upload
from django import forms

from core.models import Food, Restaurant, Category


class FoodForm(forms.ModelForm):

    class Meta:
        model = Food

        fields = [
            "restaurant",
            "category",
            "name",
            "description",
            "image",
            "price",
            "discount_price",
            "preparation_time",
            "calories",
            "is_available",
            "is_featured",
            "is_today_special",
        ]

        widgets = {

            "restaurant": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "category": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Food name"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe this food item"
                }
            ),

            "image": forms.ClearableFileInput(
                attrs={
                    "class": "form-control"
                }
            ),

            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Regular price",
                    "step": "0.01"
                }
            ),

            "discount_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Discount price",
                    "step": "0.01"
                }
            ),

            "preparation_time": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Minutes"
                }
            ),

            "calories": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Calories"
                }
            ),

            "is_available": forms.CheckboxInput(
                attrs={
                    "class": "form-checkbox"
                }
            ),

            "is_featured": forms.CheckboxInput(
                attrs={
                    "class": "form-checkbox"
                }
            ),

            "is_today_special": forms.CheckboxInput(
                attrs={
                    "class": "form-checkbox"
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop("user", None)

        super().__init__(*args, **kwargs)

        if user:

            restaurants = Restaurant.objects.filter(
                owner=user
            )

            self.fields["restaurant"].queryset = restaurants

            self.fields["category"].queryset = Category.objects.filter(
                restaurant__owner=user
            )

    def clean_image(self):
        return validate_image_upload(self.cleaned_data.get("image"))

    def clean(self):
        data = super().clean()
        restaurant, category = data.get("restaurant"), data.get("category")
        if restaurant and category and category.restaurant_id != restaurant.pk:
            self.add_error("category", "Select a category belonging to this restaurant.")
        price, discount = data.get("price"), data.get("discount_price")
        if price is not None and price <= 0:
            self.add_error("price", "Price must be greater than zero.")
        if discount is not None and (discount <= 0 or (price is not None and discount >= price)):
            self.add_error("discount_price", "Discount price must be positive and lower than regular price.")
        return data


class RestaurantSettingsForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ["name", "description", "address", "phone", "email", "opening_time", "closing_time", "delivery_fee", "minimum_order", "is_open", "logo", "cover_image"]

    def clean(self):
        data = super().clean()
        for name in ("delivery_fee", "minimum_order"):
            if data.get(name) is not None and data[name] < 0:
                self.add_error(name, "Amount cannot be negative.")
        return data


    def clean_logo(self):
        return validate_image_upload(self.cleaned_data.get("logo"))

    def clean_cover_image(self):
        return validate_image_upload(self.cleaned_data.get("cover_image"))
