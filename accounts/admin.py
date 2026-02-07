# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin configuration for User model"""
    
    # Display fields in the list view
    list_display = [
        'email', 'username', 'first_name', 'last_name', 
        'subscription_tier', 'api_quota_remaining', 
        'is_staff', 'is_active', 'created_at'
    ]
    
    # Filters for the sidebar
    list_filter = [
        'subscription_tier', 'is_staff', 'is_superuser', 
        'is_active', 'created_at', 'api_quota_reset_at'
    ]
    
    # Search fields
    search_fields = ['email', 'username', 'first_name', 'last_name']
    
    # Ordering
    ordering = ['-created_at']
    
    # Read-only fields
    readonly_fields = ['id', 'created_at', 'updated_at', 'api_quota_reset_at']
    
    # Fieldsets for the detail view
    fieldsets = (
        (None, {'fields': ('id', 'email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'avatar_url')}),
        (_('Subscription & API'), {
            'fields': ('subscription_tier', 'api_quota_remaining', 'api_quota_reset_at'),
            'classes': ('collapse',)
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    # Fieldsets for the add user view
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
    
    # Actions
    actions = ['reset_api_quota', 'upgrade_to_pro', 'upgrade_to_enterprise', 'downgrade_to_free']
    
    def reset_api_quota(self, request, queryset):
        """Reset API quota for selected users"""
        from django.utils import timezone
        updated = queryset.update(api_quota_remaining=100, api_quota_reset_at=timezone.now())
        self.message_user(request, f'{updated} users\' API quota has been reset.')
    reset_api_quota.short_description = 'Reset API quota to 100'
    
    def upgrade_to_pro(self, request, queryset):
        """Upgrade selected users to Pro tier"""
        updated = queryset.update(subscription_tier='pro')
        self.message_user(request, f'{updated} users upgraded to Pro.')
    upgrade_to_pro.short_description = 'Upgrade to Pro'
    
    def upgrade_to_enterprise(self, request, queryset):
        """Upgrade selected users to Enterprise tier"""
        updated = queryset.update(subscription_tier='enterprise')
        self.message_user(request, f'{updated} users upgraded to Enterprise.')
    upgrade_to_enterprise.short_description = 'Upgrade to Enterprise'
    
    def downgrade_to_free(self, request, queryset):
        """Downgrade selected users to Free tier"""
        updated = queryset.update(subscription_tier='free')
        self.message_user(request, f'{updated} users downgraded to Free.')
    downgrade_to_free.short_description = 'Downgrade to Free'