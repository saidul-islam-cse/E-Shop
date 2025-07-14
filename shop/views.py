from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .models import Category, Product, Cart, CartItem, Rating, Order, OrderItem
from django.contrib import messages
from .forms import RegistrationForm, RatingForm, CheckoutForm

# Create your views here.
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('shop:profile')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'shop/login.html')


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration Successful!')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'shop/register.html', {'form' : form})


def logout_view(request):
    logout(request)
    return redirect('shop:login')
