# investigations/urls.py

from django.urls import path, include
from rest_framework_nested import routers
from .views import InvestigationViewSet, SubTaskViewSet

app_name = 'investigations'

# Main router
router = routers.DefaultRouter()
router.register(r'', InvestigationViewSet, basename='investigation')

# Nested router for entities (will be added from entities app)
investigations_router = routers.NestedDefaultRouter(router, r'', lookup='investigation')

urlpatterns = [
    path('', include(router.urls)),
]