from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.db.models import Sum, F
from decimal import Decimal, ROUND_HALF_UP



# ----------- Custom FileField for returning URLs -----------
class CustomFileField(models.FileField):
    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return value.url if value else ''


# ----------- USER MODEL -----------
class User(AbstractUser):
    '''
    AbstractUser → A built-in Django base class that provides all standard authentication fields 
    (like username, email, password, first_name, last_name, is_staff, is_active, is_superuser, last_login, date_joined) 
    and built-in permission handling 

    '''
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('disabled', 'Disabled'),
        ('pending', 'Pending'),
    ]

    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')


    def __str__(self):
        return f"{self.username} ({self.role})"

# ----------- VENDOR MODEL -----------
class Vendor(models.Model):
    vendor_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    company_name = models.CharField(max_length=150)
    gst_number = models.CharField(max_length=30)
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.0)

    def __str__(self):
        return self.company_name
    
    @property
    def total_products(self):
        return self.products.count()

    @property
    def total_sales(self):
        return (
            self.products
            .filter(order_items__order__payment_status='paid')
            .aggregate(total=Sum(models.F('order_items__unit_price') * models.F('order_items__quantity')))['total'] or 0
        )



# ----------- CATEGORY MODEL -----------
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = CustomFileField(upload_to='category_images/', null=True, blank=True)

    def __str__(self):
        return self.category_name
    
    @property
    def product_count(self):
        return self.products.count()
    
    @property
    def most_ordered(self):
        results = []  
        for product in self.products.all():            
            agg = product.order_items.aggregate(total=Sum('quantity'))  
            total = int(agg['total'] or 0)             
            results.append((product, total))
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# ----------- PRODUCT MODEL -----------
class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=100)
    subname =  models.CharField(max_length=100,null=True,default="")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    unit = models.CharField(max_length=10,default="pcs")  # e.g., kg, lb, pcs, etc.
    image = CustomFileField(upload_to='product_images/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    @property
    def is_in_stock(self):
        return self.stock > 0


# ----------- CART ITEM MODEL -----------
class CartItem(models.Model):
    cart_item_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_entries')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.product.price
    
    @property
    def product_name(self):
        return self.product.name


# ----------- ORDER MODEL -----------
class Order(models.Model):
    PAYMENT_STATUS = [
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    ORDER_STATUS = [
        ('placed', 'Placed'),
        ('processing', 'Processing'),
        ('dispatched', 'Dispatched'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    order_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='paid')
    order_status = models.CharField(max_length=12, choices=ORDER_STATUS, default='placed')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.order_id} - {self.user.username}"
    
    @property
    def item_count(self):
        return self.items.count() 

    @property
    def total_before_tax(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_tax(self):
        return self.total_before_tax * 0.18  

    @property
    def grand_total(self):
        total = self.total_before_tax + self.total_tax

        return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    

# ----------- ORDER ITEM MODEL -----------
class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"
