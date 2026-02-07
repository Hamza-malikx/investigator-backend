from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ThoughtChainViewSet, AgentDecisionViewSet

app_name = 'agents'

router = DefaultRouter()
router.register(r'thoughts', ThoughtChainViewSet, basename='thought')
router.register(r'decisions', AgentDecisionViewSet, basename='decision')

urlpatterns = [
    path('', include(router.urls)),
]