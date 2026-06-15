"""
Advanced Django REST Framework Boilerplate
Complete Django project setup with models, serializers, views, and utilities.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import hashlib
import uuid
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, F, Sum, Count, Avg

from rest_framework import serializers, viewsets, status, filters, generics, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.authentication import TokenAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.authtoken.models import Token

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

# ============================================================================
# MANAGERS & CUSTOM QUERYSETS
# ============================================================================

class CustomUserManager(BaseUserManager):
    """Custom manager for User model"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)

class ActiveQuerySet(models.QuerySet):
    """QuerySet for filtering active records"""

    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def recent(self, days=7):
        cutoff = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff)

class ActiveManager(models.Manager):
    """Manager for active records"""

    def get_queryset(self):
        return ActiveQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def recent(self, days=7):
        return self.get_queryset().recent(days=days)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(AbstractUser):
    """Extended User model with custom fields"""

    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('user', 'Regular User'),
    )

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()
    active_objects = ActiveManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.verification_token:
            self.verification_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

        if not hasattr(self, '_token_created'):
            Token.objects.get_or_create(user=self)

class Category(models.Model):
    """Product/Content Category"""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveManager()

    class Meta:
        db_table = 'categories'
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Tag(models.Model):
    """Tags for content organization"""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#3b82f6')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ActiveManager()

    class Meta:
        db_table = 'tags'
        ordering = ['name']

    def __str__(self):
        return self.name

class Product(models.Model):
    """Product model with advanced features"""

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=500)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    tags = models.ManyToManyField(Tag, blank=True, related_name='products')

    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10)

    manufacturer = models.CharField(max_length=100, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    barcode = models.CharField(max_length=100, blank=True)

    weight = models.FloatField(null=True, blank=True, help_text="Weight in kg")
    dimensions = models.CharField(max_length=50, blank=True, help_text="L x W x H in cm")

    image = models.ImageField(upload_to='products/')
    images = models.ManyToManyField('ProductImage', blank=True, related_name='product_images')

    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    review_count = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_discount_percentage(self):
        if self.discount_price and self.price:
            return ((self.price - self.discount_price) / self.price) * 100
        return 0

    def is_low_stock(self):
        return self.stock <= self.low_stock_threshold

class ProductImage(models.Model):
    """Additional product images"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='product_images/')
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        ordering = ['order']

    def __str__(self):
        return f"Image for product {self.id}"

class Order(models.Model):
    """Order model"""

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    shipping_address = models.TextField()
    billing_address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Order {self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            self.order_number = f"ORD-{timestamp}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    """Items in an order"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)

    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f"Item in {self.order.order_number}"

class Review(models.Model):
    """Product reviews"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    content = models.TextField()

    helpful_count = models.IntegerField(default=0)
    unhelpful_count = models.IntegerField(default=0)

    is_verified_purchase = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveManager()

    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        unique_together = ('product', 'user')

    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"

class Newsletter(models.Model):
    """Newsletter subscription"""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'newsletters'

    def __str__(self):
        return self.email

class ContactMessage(models.Model):
    """Contact form messages"""

    STATUS_CHOICES = (
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    )

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    reply = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contact_messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name}"

# ============================================================================
# SERIALIZERS
# ============================================================================

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'password',
                  'phone_number', 'role', 'bio', 'is_verified', 'created_at')
        read_only_fields = ('id', 'created_at', 'is_verified')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category"""

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'icon', 'parent', 'order', 'is_active')

class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag"""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug', 'description', 'color', 'is_active')

class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage"""

    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'order')

class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product"""

    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    discount_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'description', 'short_description', 'category',
                  'category_name', 'price', 'discount_price', 'discount_percentage',
                  'stock', 'sku', 'rating', 'review_count', 'status', 'featured',
                  'images', 'created_at', 'updated_at')

    def get_discount_percentage(self, obj):
        return obj.get_discount_percentage()

class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review"""

    user_name = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'product', 'rating', 'title', 'content', 'user_name',
                  'helpful_count', 'unhelpful_count', 'is_verified_purchase', 'created_at')

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem"""

    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'price', 'total')

class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order"""

    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'order_number', 'user', 'user_email', 'subtotal', 'tax',
                  'shipping', 'discount', 'total', 'status', 'items', 'created_at', 'updated_at')

# ============================================================================
# VIEWSETS & VIEWS
# ============================================================================

class StandardPagination(PageNumberPagination):
    """Standard pagination for list views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User management"""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username']
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        """Change user password"""
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        serializer = serializers.Serializer(
            old_password=serializers.CharField(),
            new_password=serializers.CharField()
        )

        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Invalid password'}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'status': 'password set'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category"""

    queryset = Category.objects.active()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filterset_fields = ['parent', 'is_active']

class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for Tag"""

    queryset = Tag.objects.active()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for Product"""

    queryset = Product.objects.filter(status='published', is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'featured']
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['created_at', 'price', 'rating']
    pagination_class = StandardPagination

    @action(detail=True, methods=['post'])
    def add_to_cart(self, request, pk=None):
        """Add product to cart"""
        product = self.get_object()
        quantity = request.data.get('quantity', 1)

        if product.stock < quantity:
            return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'added to cart', 'product_id': str(product.id)})

class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Review"""

    queryset = Review.objects.filter(is_active=True)
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at', 'helpful_count']
    pagination_class = StandardPagination

class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for Order"""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Get current user's orders"""
        orders = Order.objects.filter(user=request.user)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = uuid.uuid4().hex[:8].upper()
    return f"ORD-{timestamp}-{random_suffix}"

def calculate_order_total(items: List[Dict[str, Any]], tax_rate: float = 0.1, shipping: Decimal = Decimal('0')) -> Dict[str, Decimal]:
    """Calculate order totals"""
    subtotal = sum(Decimal(str(item['price'])) * item['quantity'] for item in items)
    tax = subtotal * Decimal(str(tax_rate))
    total = subtotal + tax + shipping

    return {
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'shipping': shipping
    }

def send_order_confirmation(order: Order):
    """Send order confirmation email"""
    subject = f"Order Confirmation #{order.order_number}"
    message = f"Your order {order.order_number} has been confirmed."
    return True

@api_view(['POST'])
@permission_classes([AllowAny])
def contact_us(request):
    """Handle contact form submissions"""
    serializer = serializers.Serializer(
        name=serializers.CharField(),
        email=serializers.EmailField(),
        subject=serializers.CharField(),
        message=serializers.CharField()
    )

    if serializer.is_valid():
        ContactMessage.objects.create(**serializer.validated_data)
        return Response({'status': 'Message sent successfully'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def newsletter_subscribe(request):
    """Handle newsletter subscriptions"""
    email = request.data.get('email')

    if not email:
        return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)

    newsletter, created = Newsletter.objects.get_or_create(email=email)

    if created:
        return Response({'status': 'Subscribed successfully'}, status=status.HTTP_201_CREATED)
    return Response({'status': 'Already subscribed'})

# ============================================================================
# URL CONFIGURATION (urls.py equivalent)
# ============================================================================

"""
Example URL patterns:

from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/contact/', contact_us, name='contact'),
    path('api/newsletter/', newsletter_subscribe, name='newsletter'),
    path('api-auth/', include('rest_framework.urls')),
]
"""

# ============================================================================
# ADDITIONAL UTILITIES & HELPERS
# ============================================================================

class PriceHelper:
    """Helper methods for price calculations"""

    @staticmethod
    def apply_discount(price: Decimal, discount_percentage: float) -> Decimal:
        """Calculate price after discount"""
        return price * Decimal(str(1 - discount_percentage / 100))

    @staticmethod
    def calculate_profit(price: Decimal, cost: Decimal) -> Decimal:
        """Calculate profit"""
        return price - cost

    @staticmethod
    def calculate_margin(price: Decimal, cost: Decimal) -> float:
        """Calculate profit margin percentage"""
        if cost == 0:
            return 0
        return ((price - cost) / price) * 100

class InventoryHelper:
    """Helper methods for inventory management"""

    @staticmethod
    def check_stock_availability(product: Product, quantity: int) -> bool:
        """Check if product has sufficient stock"""
        return product.stock >= quantity

    @staticmethod
    def update_stock(product: Product, quantity: int, operation: str = 'decrease'):
        """Update product stock"""
        if operation == 'decrease':
            product.stock -= quantity
        elif operation == 'increase':
            product.stock += quantity
        product.save()

    @staticmethod
    def get_low_stock_products() -> List[Product]:
        """Get all products with low stock"""
        return Product.objects.filter(stock__lte=F('low_stock_threshold'), is_active=True)

class NotificationHelper:
    """Helper methods for notifications"""

    @staticmethod
    def notify_order_status_change(order: Order, new_status: str):
        """Notify user of order status change"""
        pass

    @staticmethod
    def notify_low_stock(product: Product):
        """Notify admin of low stock"""
        pass

    @staticmethod
    def notify_new_review(product: Product, review: Review):
        """Notify admin of new review"""
        pass

class ReportGenerator:
    """Generate reports from order and product data"""

    @staticmethod
    def generate_sales_report(start_date, end_date):
        """Generate sales report for date range"""
        orders = Order.objects.filter(
            created_at__range=[start_date, end_date],
            status__in=['delivered', 'shipped']
        )

        total_revenue = orders.aggregate(Sum('total'))['total__sum'] or Decimal('0')
        total_orders = orders.count()
        average_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')

        return {
            'period': f"{start_date} to {end_date}",
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'average_order_value': average_order_value,
        }

    @staticmethod
    def generate_product_performance_report():
        """Generate product performance report"""
        products = Product.objects.annotate(
            total_sales=Count('orderitem'),
            avg_rating=Avg('reviews__rating')
        ).filter(total_sales__gt=0).order_by('-total_sales')

        return [
            {
                'product_id': str(p.id),
                'name': p.name,
                'total_sales': p.total_sales,
                'avg_rating': p.avg_rating or 0,
                'revenue': p.price * p.total_sales,
            }
            for p in products[:50]
        ]

    @staticmethod
    def generate_customer_report():
        """Generate customer analytics report"""
        users = User.objects.annotate(
            order_count=Count('orders'),
            total_spent=Sum('orders__total')
        ).filter(order_count__gt=0).order_by('-total_spent')

        return [
            {
                'user_id': u.id,
                'email': u.email,
                'order_count': u.order_count,
                'total_spent': u.total_spent or Decimal('0'),
                'average_order_value': (u.total_spent or Decimal('0')) / u.order_count if u.order_count > 0 else Decimal('0'),
            }
            for u in users[:100]
        ]

class SearchHelper:
    """Helper for advanced search functionality"""

    @staticmethod
    def search_products(query: str, category_id: Optional[int] = None, min_price: Decimal = None, max_price: Decimal = None):
        """Advanced product search"""
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query),
            status='published',
            is_active=True
        )

        if category_id:
            products = products.filter(category_id=category_id)
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)

        return products.order_by('-rating', '-review_count')

    @staticmethod
    def search_users(query: str):
        """Search users by email or name"""
        return User.objects.filter(
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            is_active=True
        )

class ValidationHelper:
    """Helper for custom validations"""

    @staticmethod
    def validate_email_format(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        import re
        pattern = r'^\+?1?\d{9,15}$'
        return bool(re.match(pattern, phone))

    @staticmethod
    def validate_sku(sku: str) -> bool:
        """Validate SKU format"""
        return len(sku) >= 4 and len(sku) <= 20 and sku.isalnum()

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not any(char.isupper() for char in password):
            return False, "Password must contain at least one uppercase letter"
        if not any(char.islower() for char in password):
            return False, "Password must contain at least one lowercase letter"
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one digit"
        return True, "Password is strong"

class CacheHelper:
    """Helper for caching operations"""

    @staticmethod
    def get_cache_key(prefix: str, *args) -> str:
        """Generate cache key"""
        return f"{prefix}:{'_'.join(str(arg) for arg in args)}"

    @staticmethod
    def invalidate_product_cache(product_id):
        """Invalidate product-related caches"""
        from django.core.cache import cache
        cache_keys = [
            CacheHelper.get_cache_key('product', product_id),
            CacheHelper.get_cache_key('product_reviews', product_id),
            'products_list',
        ]
        for key in cache_keys:
            cache.delete(key)

class LoggingHelper:
    """Helper for logging and audit trails"""

    @staticmethod
    def log_order_action(order: Order, action: str, user: User, details: str = ""):
        """Log order-related actions"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] Order {order.order_number}: {action} by {user.email} - {details}"
        return log_entry

    @staticmethod
    def log_product_change(product: Product, field: str, old_value, new_value, user: User):
        """Log product changes"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] Product {product.id}: {field} changed from {old_value} to {new_value} by {user.email}"
        return log_entry

class ExportHelper:
    """Helper for data export functionality"""

    @staticmethod
    def export_orders_to_csv(orders, filename: str = "orders.csv"):
        """Export orders to CSV"""
        import csv
        rows = []
        for order in orders:
            rows.append({
                'order_number': order.order_number,
                'customer_email': order.email,
                'total': order.total,
                'status': order.status,
                'created_at': order.created_at.isoformat(),
            })
        return rows

    @staticmethod
    def export_products_to_json(products):
        """Export products to JSON"""
        return [
            {
                'id': str(p.id),
                'name': p.name,
                'price': str(p.price),
                'stock': p.stock,
                'rating': p.rating,
            }
            for p in products
        ]

class AnalyticsHelper:
    """Helper for analytics calculations"""

    @staticmethod
    def calculate_conversion_rate(total_visitors: int, total_buyers: int) -> float:
        """Calculate conversion rate"""
        return (total_buyers / total_visitors * 100) if total_visitors > 0 else 0

    @staticmethod
    def calculate_cart_abandonment_rate(total_carts: int, completed_orders: int) -> float:
        """Calculate cart abandonment rate"""
        return ((total_carts - completed_orders) / total_carts * 100) if total_carts > 0 else 0

    @staticmethod
    def get_best_selling_products(limit: int = 10):
        """Get best selling products"""
        from django.db.models import Count
        return Product.objects.annotate(
            sale_count=Count('orderitem')
        ).order_by('-sale_count')[:limit]

    @staticmethod
    def get_trending_products(days: int = 30, limit: int = 10):
        """Get trending products from recent orders"""
        from django.db.models import Count
        cutoff_date = timezone.now() - timedelta(days=days)
        return Product.objects.filter(
            orderitem__order__created_at__gte=cutoff_date
        ).annotate(
            recent_sales=Count('orderitem')
        ).order_by('-recent_sales')[:limit]

class SecurityHelper:
    """Helper for security-related operations"""

    @staticmethod
    def hash_password_sha256(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate secure random token"""
        return uuid.uuid4().hex + uuid.uuid4().hex  # Return enough for desired length

    @staticmethod
    def is_ip_whitelisted(ip_address: str, whitelist: List[str]) -> bool:
        """Check if IP is in whitelist"""
        return ip_address in whitelist

class DateHelper:
    """Helper for date/time operations"""

    @staticmethod
    def get_date_range(range_type: str):
        """Get date range based on type"""
        today = timezone.now().date()

        if range_type == 'today':
            return today, today
        elif range_type == 'week':
            return today - timedelta(days=today.weekday()), today
        elif range_type == 'month':
            return today.replace(day=1), today
        elif range_type == 'year':
            return today.replace(month=1, day=1), today
        return today, today

    @staticmethod
    def format_date_range(start_date, end_date) -> str:
        """Format date range for display"""
        return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

class PaginationHelper:
    """Helper for pagination calculations"""

    @staticmethod
    def get_page_info(total_count: int, page_size: int, current_page: int) -> dict:
        """Calculate pagination info"""
        total_pages = (total_count + page_size - 1) // page_size
        offset = (current_page - 1) * page_size
        has_next = current_page < total_pages
        has_previous = current_page > 1

        return {
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': current_page,
            'page_size': page_size,
            'offset': offset,
            'has_next': has_next,
            'has_previous': has_previous,
        }

# End of Django DRF Boilerplate
