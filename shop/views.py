from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from .models import Category, Product, Cart, CartItem, Rating, Order, OrderItem, CustomUser
from django.contrib import messages
from .forms import RegistrationForm, RatingForm, CheckoutForm
from django.db.models import Q, Min, Max, Avg
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .utils import generate_sslcommerz_payment, send_order_confirmation_email, send_verification_email

# Create your views here.
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None and user.is_active==True:
            login(request, user)
            return redirect('shop:profile')
        else:
            messages.error(request, 'Invalid email or password')

    return render(request, 'shop/login.html')


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            send_verification_email(request, user)
            messages.info(request, "We have sent you an verification email")
            return redirect('shop:login')
    else:
        form = RegistrationForm()
    return render(request, 'shop/register.html', {'form' : form})



def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.is_active = True
        user.save()
        messages.success(request, "Your email has been verified successfully.")
        return redirect('shop:login')
    else:
        messages.error(request, "The verification link is invalid or has expired.")
        return redirect('shop:register')
   
def logout_view(request):
    logout(request)
    return redirect('shop:login')


def home(request):
    featured_products = Product.objects.filter(available=True).order_by('-created')[:8]
    categories = Category.objects.all()

    return render(request, 'shop/home.html', {
        'featured_products' : featured_products,
        'categories' : categories
    })

def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available = True)

    if category_slug :
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    
    min_price = products.aggregate(Min('price'))['price__min']
    max_price = products.aggregate(Max('price'))['price__max']

    if request.GET.get('min_price'):
        products = products.filter(price__gte=request.GET.get('min_price'))
    if request.GET.get('max_price'):
        products = products.filter(price__lte=request.GET.get('max_price'))
    if request.GET.get('rating'):
        min_rating = request.GET.get('rating')
        products = products.annotate(avg_rating=Avg('ratings__rating')).filter(avg_rating__gte=min_rating)
    
    if request.GET.get('search'):
        query = request.GET.get('search')
        products = products.filter(
            Q(name__icontains = query) |
            Q(description__icontains = query) |
            Q(category__name__icontains = query) 
        )
    return render(request, 'shop/product_list.html', {
        'category' : category,
        'categories' : categories,
        'products' : products,
        'min_price' : min_price,
        'max_price' : max_price
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available = True)
    related_products = Product.objects.filter(category = product.category).exclude(id=product.id)
    user_rating = None

    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(product=product, user=request.user)
        except Rating.DoesNotExist:
            pass 
    rating_form = RatingForm(instance=user_rating)

    return render(request, 'shop/product_detail.html', {
        'product' : product,
        'related_products' : related_products,
        'user_rating' : user_rating,
        'rating_form' : rating_form
    })

@login_required(login_url='/login/')
def cart_detail(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)

    return render(request, 'shop/cart.html', {'cart' : cart})

@login_required(login_url='/login/')
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
    
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.quantity += 1
        cart_item.save()
    except CartItem.DoesNotExist:
        CartItem.objects.create(cart=cart, product=product, quantity = 1)

    messages.success(request, f"{product.name} has been added to your cart!")
    return redirect('shop:product_detail', slug=product.slug)


@login_required(login_url='/login/')
def cart_remove(request, product_id):
    cart = get_object_or_404(Cart, user= request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    cart_item.delete()
    messages.success(request, f"{product.name} has been removed from your cart!")
    return redirect('shop:cart_detail')

@login_required(login_url='/login/')
def cart_update(request, product_id):
    cart = get_object_or_404(Cart, user= request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)

    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        cart_item.delete()
        messages.success(request, f"{product.name} has been removed from your cart!")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"Cart Updated successfully!!")
    return redirect('shop:cart_detail')


@csrf_exempt
@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            messages.warning(request, 'Your cart is empty!')
            return redirect('shop:cart_detail')
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty!')
        return redirect('shop:cart_detail')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()

            for item in cart.items.all():
                OrderItem.objects.create(
                    order = order,
                    product = item.product,
                    price = item.product.price,
                    quantity = item.quantity
                )
            cart.items.all().delete()
            request.session['order_id'] = order.id 
            return redirect('shop:payment_process')
    else:
        initial_data = {}
        if request.user.first_name:
            initial_data['first_name'] = request.user.first_name
        if request.user.last_name:
            initial_data['last_name'] = request.user.last_name
        if request.user.email:
            initial_data['email'] = request.user.email
        
        form = CheckoutForm(initial=initial_data)
    
    return render(request, 'shop/checkout.html' , {
        'cart' : cart,
        'form' : form
    })
        

@csrf_exempt
@login_required
def payment_process(request):
    order_id = request.session.get('order_id')
    if not order_id:
        return redirect('shop:home')
    
    order = get_object_or_404(Order, id=order_id)
    payment_data = generate_sslcommerz_payment(order, request)

    if payment_data['status'] == 'SUCCESS':
        return redirect(payment_data['GatewayPageURL'])
    else:
        messages.error(request, "Payment gateway error. Please Try again.")
        return redirect('shop:checkout')

@csrf_exempt
@login_required
def payment_success(request, order_id):
    order= get_object_or_404(Order, id= order_id, user=request.user)
    order.paid = True
    order.status = 'processing'
    order.transaction_id = order.id 
    order.save()

    order_items = order.items.all()
    for item in order_items:
        product = item.product
        product.stock -= item.quantity

        if product.stock < 0:
            product.stock = 0
        product.save()
    
    send_order_confirmation_email(order)
    messages.success(request, "Payment successful")
    return render(request, 'shop/payment_success.html', {'order': order})

@csrf_exempt
@login_required
def payment_fail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user= request.user)
    order.status = 'canceled'
    order.save()
    return redirect('shop:checkout')


@csrf_exempt
@login_required
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user= request.user)
    order.status = 'canceled'
    order.save()
    return redirect('shop:cart_detail')

@login_required(login_url='/login/')
def profile(request):
    tab = request.GET.get('tab')
    orders = Order.objects.filter(user=request.user).order_by('-created')
    completed_orders = orders.filter(status = 'delivered').count()
    total_spent = sum(order.get_total_cost() for order in orders if order.paid)
    order_history_active = (tab == 'orders')

    return render(request, 'shop/profile.html', {
        'user' : request.user,
        'orders' : orders,
        'order_history_active' : order_history_active,
        'completed_orders' : completed_orders,
        'total_spent' : total_spent
    })

@login_required(login_url='/login/')
def rate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    ordered_items = OrderItem.objects.filter(
        order__user = request.user,
        order__paid = True,
        product= product
    )

    if not ordered_items.exists():
        messages.warning(request, 'You can only rate products you have purchased')
        return redirect('shop:product_detail', slug = product.slug)
    try:
        rating = Rating.objects.get(product=product, user=request.user)
    except Rating.DoesNotExist:
        rating = None 
    
    if request.method == 'POST':
        form = RatingForm(request.POST, instance = rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.product = product 
            rating.user = request.user 
            rating.save()
            return redirect('shop:product_detail', slug=product.slug)
    else:
        form = RatingForm(instance=rating)
    
    return render(request, 'shop/rate_product.html', {
        'form' : form,
        'product' : product
    })


def custom_404_view(request, exception):
    return render(request, 'shop/404.html', status=404)