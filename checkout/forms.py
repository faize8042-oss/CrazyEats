from django import forms
from django.core.validators import RegexValidator

class CheckoutForm(forms.Form):
    address = forms.CharField(min_length=8, max_length=1000)
    phone = forms.CharField(max_length=20, validators=[RegexValidator(r"^\+?[0-9 ()-]{7,20}$", "Enter a valid delivery phone number.")])
    payment_method = forms.ChoiceField(choices=[("cod", "Cash on Delivery")])
    instructions = forms.CharField(required=False, max_length=2000)
