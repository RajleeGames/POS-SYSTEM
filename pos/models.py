import logging
import uuid
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# Category Model
# ----------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------------------
# Supplier Model
# ----------------------------------------------------------------
class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=100)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------------------
# Product Model
# ----------------------------------------------------------------
class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    barcode = models.CharField(max_length=50, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True
    )
    expiration_date = models.DateField(null=True, blank=True)
    reorder_level = models.IntegerField(default=10)  # Low stock alert

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate a 12-digit barcode if none is set
        if not self.barcode:
            self.barcode = str(uuid.uuid4().int)[:12]
        super().save(*args, **kwargs)

    def reduce_stock(self, quantity):
        if self.stock < quantity:
            raise ValueError("Not enough stock to reduce")
        self.stock -= quantity
        self.save()


# ----------------------------------------------------------------
# Customer Model
# ----------------------------------------------------------------
class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------------------
# SaleItem Model (uses a forward reference to 'Sale')
# ----------------------------------------------------------------
class SaleItem(models.Model):
    """
    For multi-item sales (and now single-item too),
    each line item references a product, quantity, and total price.
    """
    sale = models.ForeignKey(
        'Sale',  # forward reference, since Sale is defined below
        on_delete=models.CASCADE,
        related_name='items'
    )
    cashier = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, null=True, blank=True
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - Qty: {self.quantity} - Total: Tsh{self.total_price}"


# ----------------------------------------------------------------
# Sale Model
# ----------------------------------------------------------------
class Sale(models.Model):
    """
    If it's a single-item sale, 'product' & 'quantity' are set,
    and we auto-create a matching SaleItem upon first save.
    For multi-item sales, those details live in SaleItem, and
    'product'/'quantity' remain blank.
    """
    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.SET_NULL
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(null=True, blank=True)
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ("cash", "Cash"),
            ("card", "Card"),
            ("mobile_money", "Mobile Money")
        ],
    )
    date = models.DateTimeField(auto_now_add=True)
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        is_new_sale = self.pk is None  # check if this is a brand-new sale

        # Handle single-item sale logic
        if self.product is not None:
            if not self.quantity:
                raise ValueError("Quantity cannot be None for a single–item sale.")
            self.total_price = Decimal(self.product.price) * Decimal(self.quantity)

            # Check for any applicable discount
            discount_qs = Discount.objects.filter(
                product=self.product,
                start_date__lte=self.date if self.date else datetime.now(),
                end_date__gte=self.date if self.date else datetime.now()
            )
            discount = discount_qs.first()
            if discount:
                discount_factor = (1 - Decimal(discount.discount_percentage) / 100)
                self.total_price *= discount_factor
                logger.debug(f"Discount Applied: {discount.discount_percentage}%")

            self.total_amount = self.total_price

            # Reduce stock only on the first save
            if is_new_sale:
                logger.debug(f"Reducing stock: {self.product.stock} -> {self.product.stock - self.quantity}")
                self.product.reduce_stock(self.quantity)

        # Save the Sale itself
        super().save(*args, **kwargs)

        # If it's a new single-item sale, ensure a SaleItem exists
        if is_new_sale and self.product and self.quantity and not self.items.exists():
            SaleItem.objects.create(
                sale=self,
                cashier=self.cashier,
                product=self.product,
                quantity=self.quantity,
                total_price=self.total_price or Decimal('0.00')
            )

    def print_receipt_link(self):
        if self.id:
            url = reverse("generate_receipt", args=[self.id])
            return format_html(
                '<a class="button" href="{}" target="_blank">Print Receipt</a>', url
            )
        return "-"

    print_receipt_link.short_description = "Print Receipt"

    def __str__(self):
        if self.product:
            return f"{self.quantity} x {self.product.name} - {self.total_price}"
        else:
            return f"Sale #{self.id} - Total: {self.total_amount}"


# ----------------------------------------------------------------
# Discount Model
# ----------------------------------------------------------------
class Discount(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return f"{self.product.name} - {self.discount_percentage}%"


# ----------------------------------------------------------------
# Stock Movement Model
# ----------------------------------------------------------------
class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUST', 'Stock Adjustment'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Update stock based on movement type
        if self.movement_type == 'IN':
            self.product.stock += self.quantity
        elif self.movement_type == 'OUT':
            self.product.stock -= self.quantity
        elif self.movement_type == 'ADJUST':
            self.product.stock = self.quantity
        
        self.product.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} ({self.quantity})"


# ----------------------------------------------------------------
# Contact Model
# ----------------------------------------------------------------
class Contact(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------------------
# Expense Model
# ----------------------------------------------------------------
class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)  # Automatically set to today's date

    def __str__(self):
        return self.description


class CompanyInfo(models.Model):
    company_name = models.CharField(max_length=255, default="Supermarket POS")
    ceo_name = models.CharField(max_length=255, blank=True)
    ceo_image = models.ImageField(upload_to='ceo_images/', blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.company_name or "Company Info"


class LoginLog(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} logged in at {self.login_time}"


class PaymentMethod(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.ImageField(upload_to='payment_icons/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.message}"
