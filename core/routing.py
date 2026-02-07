from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Investigation real-time updates
    re_path(
        r'ws/investigations/(?P<investigation_id>[0-9a-f-]+)/$',
        consumers.InvestigationConsumer.as_asgi()
    ),
    
    # Board real-time updates
    re_path(
        r'ws/board/(?P<investigation_id>[0-9a-f-]+)/$',
        consumers.BoardConsumer.as_asgi()
    ),
]