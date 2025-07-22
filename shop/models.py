from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

# Create your models here.

class CustomUser(AbstractUser):
    is_verified = models.BooleanField(default=False)
    username = None

    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(null=True, blank=True, upload_to="user_profile")

    objects = CustomUserManager()
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name 

class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # 122.23
    stock = models.PositiveBigIntegerField(default=1)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d')

    def __str__(self):
        return self.name 
    
    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.count() > 0:
            return sum([rating.rating for rating in ratings])/ratings.count()
        return 0


class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}"


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"
    
    def get_total_price(self):
        return sum(item.get_cost() for item in self.items.all())
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())
    
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name = "items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} X {self.product.name}"
    
    def get_cost(self):
        return self.product.price*self.quantity

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(blank = True)
    paid = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=200, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"Order #{self.id}"
    
    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity} X {self.product.name}"
    
    def get_cost(self):
        return self.price*self.quantity
