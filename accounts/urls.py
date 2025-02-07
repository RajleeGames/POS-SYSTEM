# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # Make sure you have views defined in accounts/views.py

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('account-settings/', views.account_settings_view, name='account_settings'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
]
