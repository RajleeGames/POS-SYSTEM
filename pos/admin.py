from django.contrib import admin
from .models import Category, Supplier, Product, Discount, Sale, StockMovement, Customer

# Product Admin
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'category', 'supplier', 'expiration_date')
    list_filter = ('category', 'supplier', 'expiration_date')
    search_fields = ('name', 'barcode')

# Sale Admin
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'total_price', 'date', 'payment_method')
    list_filter = ('date', 'payment_method')
    search_fields = ('product__name',)
    fields = ('product', 'quantity', 'total_price', 'payment_method',)
    readonly_fields = ('total_price',)  # Make total_price read-only
    
    


# Customer Admin
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number')
    search_fields = ('name', 'email')

# Registering all models
admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Product, ProductAdmin)
admin.site.register(Discount)
admin.site.register(Sale, SaleAdmin)
admin.site.register(StockMovement)
admin.site.register(Customer, CustomerAdmin)
