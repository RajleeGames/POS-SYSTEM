from django.urls import path
from . import views
from .views import get_product_details

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cashier/', views.cashier_dashboard, name='cashier_dashboard'),
    path('sales_history/', views.sales_history, name='sales_history'),
    path('sales_report/', views.sales_report, name='sales_report'),
    path('receipt/<int:sale_id>/', views.receipt_view, name='receipt_view'),
    path('receipt/pdf/<int:sale_id>/', views.generate_receipt_pdf, name='generate_receipt_pdf'),
    path('logout/', views.logout_view, name='logout'),
    path('enhanced_sales_report/', views.enhanced_sales_report, name='enhanced_sales_report'),
    path('complete_sale/', views.complete_sale, name='complete_sale'),
    path('sale_success/', views.sale_success, name='sale_success'),
    path('signup/', views.signup_view, name='signup'),
    path('settings/', views.settings_view, name='settings'),
    path('pos/', views.pos, name='pos'),
    # New AJAX endpoints for barcode lookup and product search
    path('lookup_barcode/', views.lookup_by_barcode, name='lookup_barcode'),
    path('search_products/', views.search_products, name='search_products'),
    path('get_product_details/', get_product_details, name='get_product_details'),
]
