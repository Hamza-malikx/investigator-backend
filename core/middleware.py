from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs

User = get_user_model()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens.
    
    Token can be passed via:
    1. Query parameter: ws://localhost:8000/ws/investigations/{id}/?token=JWT_TOKEN
    2. Cookie: ws://localhost:8000/ws/investigations/{id}/ (with token in cookie)
    """
    
    async def __call__(self, scope, receive, send):
        # Get token from query string or headers
        token = self.get_token_from_scope(scope)
        
        if token:
            try:
                # Validate token and get user
                scope['user'] = await self.get_user_from_token(token)
            except (InvalidToken, TokenError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)
    
    def get_token_from_scope(self, scope):
        """Extract JWT token from WebSocket scope"""
        # Try query parameters first
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        if 'token' in query_params:
            return query_params['token'][0]
        
        # Try cookies
        cookies = scope.get('cookies', {})
        if 'access_token' in cookies:
            return cookies['access_token']
        
        # Try headers (for some WebSocket clients)
        headers = dict(scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode()
        
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        return None
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get user from JWT token"""
        try:
            # Decode and validate token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # Get user from database
            user = User.objects.get(id=user_id)
            return user
        
        except (InvalidToken, TokenError, User.DoesNotExist):
            return AnonymousUser()


# Factory function for use in ASGI application
def JWTAuthMiddlewareStack(inner):
    """Helper function to wrap JWT auth middleware"""
    return JWTAuthMiddleware(inner)