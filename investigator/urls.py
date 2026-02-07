# investigator/urls.py

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
import os

def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'debug': settings.DEBUG,
        'database': 'postgresql',
        'environment': 'development' if settings.DEBUG else 'production'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('api/v1/investigations/', include('investigations.urls')),
    path('api/v1/auth/', include('accounts.urls')),
    # path('api/v1/reviews/', include('reviews.urls')),
    # path('api/v1/notifications/', include('notifications.urls')),
    # path('api/v1/votes/', include('votes.urls')),
    # path('api/v1/cities/', include('cities.urls')),
    # path('api/v1/boosts/', include('boosts.urls')),
    # path('api/v1/telegram/', include('telegram.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
