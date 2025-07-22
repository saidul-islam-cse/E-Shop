from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User 
from .models import Rating, Order, CustomUser

class RegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating' : forms.Select(choices=[(i,i) for i in range(1,6)]),
            'comment' : forms.Textarea(attrs={'rows' : 4})
        }

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email','address', 'postal_code', 'city', 'note']
        widgets = {
            'note' : forms.Textarea(attrs={'rows' : 3})
        }