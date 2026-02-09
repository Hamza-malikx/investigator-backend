# accounts/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, CustomTokenObtainPairView, LogoutView,
    ProfileView, ChangePasswordView, dashboard_stats, recent_activity, system_status
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh-token/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # Dashboard
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('dashboard/activity/', recent_activity, name='dashboard-activity'),
    path('dashboard/system-status/', system_status, name='dashboard-system-status'),
]