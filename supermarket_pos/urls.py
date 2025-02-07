# supermarket_pos/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  # Ensure this line is there
from pos import views



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pos.urls')),  # Include the pos.urls
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),  # Login URL (no need to change)
    path('accounts/logout/', views.logout_view, name='logout'),  # Custom logout view
    path('accounts/', include('django.contrib.auth.urls')),  # Other auth URLs
    path('complete_sale/', views.complete_sale, name='complete_sale'),
    path('sale-success/', views.sale_success, name='sale_success_url'),
    path('make_sale/', views.make_sale, name='make_sale'),
    path('add_to_sale/<int:product_id>/', views.add_to_sale, name='add_to_sale'),
    path('accounts/', include('accounts.urls')),  # Ensure this line exists
]
