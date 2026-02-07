from django.urls import path, include
from rest_framework_nested import routers
from rest_framework.routers import DefaultRouter
from .views import InvestigationViewSet
from entities.views import EntityViewSet, RelationshipViewSet
from evidence.views import EvidenceViewSet
from agents.views import BoardViewSet
app_name = 'investigations'
# Main router for investigations
router = DefaultRouter()
router.register(r'', InvestigationViewSet, basename='investigation')
# Nested router for investigation resources
investigations_router = routers.NestedDefaultRouter(
    router, r'', lookup='investigation'
)
investigations_router.register(r'entities', EntityViewSet, basename='investigation-entities')
investigations_router.register(r'relationships', RelationshipViewSet, basename='investigation-relationships')
investigations_router.register(r'evidence', EvidenceViewSet, basename='investigation-evidence')
investigations_router.register(r'board', BoardViewSet, basename='investigation-board')
urlpatterns = [
    path('', include(router.urls)),
    path('', include(investigations_router.urls)),
]