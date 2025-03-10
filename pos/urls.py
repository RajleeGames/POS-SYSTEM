from django.urls import path
from . import views
from .views import get_product_details
from django.conf import settings
from django.conf.urls.static import static
from .views import product_list, contacts_list, stock_movement_list, add_expense, expense_list

# Placeholder view for additional features
def placeholder(_request):
    from django.http import HttpResponse
    return HttpResponse("This page is under construction.")

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
    path('notifications/mark_all_read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('notifications/clear_all/', views.clear_all_notifications, name='clear_all'),
    
    # AJAX endpoints
    path('lookup_barcode/', views.lookup_by_barcode, name='lookup_barcode'),
    path('search_products/', views.search_products, name='search_products'),
    path('get_product_details/', get_product_details, name='get_product_details'),
    path('products/', product_list, name='product_list'),
    path('contacts/', contacts_list, name='contacts_list'),
    path('contacts/add/', views.add_contact, name='add_contact'),
    path('contacts/edit/<int:pk>/', views.edit_contact, name='edit_contact'),
    path('contacts/delete/<int:pk>/', views.delete_contact, name='delete_contact'),
    path('stock-movement/', stock_movement_list, name='stock_movement_list'),
    path('expenses/add/', add_expense, name='add_expense'),
    path('expenses/', expense_list, name='expense_list'),
    
    # Additional Sidebar Features

    # Reports (Submenu) - Update these to point to your actual views
    path('profit_loss/', views.profit_loss_report, name='profit_loss'),
    path('inventory_report/', views.inventory_report, name='inventory_report'),
    
    # Analytics (Submenu)
    path('top_selling_products/', views.top_selling_products, name='top_selling_products'),
    path('sales_by_category/', views.sales_by_category, name='sales_by_category'),
    path('sales_by_cashier/', views.sales_by_cashier, name='sales_by_cashier'),
    
    
    # Inventory
    path('supplier_management/', views.supplier_list, name='supplier_list'),
    path('supplier_management/add/', views.add_supplier, name='add_supplier'),
    path('supplier_management/edit/<int:pk>/', views.edit_supplier, name='edit_supplier'),
    path('supplier_management/delete/<int:pk>/', views.delete_supplier, name='delete_supplier'),

    
    # Settings
    path('company_info/', views.company_info_view, name='company_info'),
    path('payment_methods/', views.payment_method_list, name='payment_method_list'),
    path('payment_methods/add/', views.add_payment_method, name='add_payment_method'),
    path('payment_methods/edit/<int:pk>/', views.edit_payment_method, name='edit_payment_method'),
    path('payment_methods/delete/<int:pk>/', views.delete_payment_method, name='delete_payment_method'),
    path('system_logs/', views.system_logs_view, name='system_logs'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
