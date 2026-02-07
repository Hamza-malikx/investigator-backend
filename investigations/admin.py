# investigations/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import Investigation, InvestigationPlan, SubTask


class SubTaskInline(admin.TabularInline):
    """Inline subtasks for Investigation admin"""
    model = SubTask
    extra = 0
    fields = ('task_type', 'description', 'status', 'confidence', 'order')
    readonly_fields = ('confidence',)
    show_change_link = True
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False  # Prevent manual creation via inline


class InvestigationPlanInline(admin.StackedInline):
    """Inline plan for Investigation admin"""
    model = InvestigationPlan
    can_delete = False
    max_num = 1
    min_num = 1
    fields = ('research_strategy', 'hypothesis', 'priority_areas', 'avoided_paths')


@admin.register(Investigation)
class InvestigationAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'user', 
        'status_badge', 
        'current_phase',
        'progress_percentage', 
        'confidence_score',
        'total_cost_usd',
        'created_at',
        'duration_display'
    )
    list_filter = ('status', 'current_phase', 'created_at')
    search_fields = ('title', 'initial_query', 'user__username', 'user__email')
    readonly_fields = (
        'id', 
        'created_at', 
        'updated_at',
        'total_api_calls',
        'total_cost_usd'
    )
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'title', 'initial_query')
        }),
        ('Status & Progress', {
            'fields': ('status', 'current_phase', 'progress_percentage', 'confidence_score')
        }),
        ('Timing', {
            'fields': (('started_at', 'completed_at', 'estimated_completion'),)
        }),
        ('Resources', {
            'fields': ('total_api_calls', 'total_cost_usd'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InvestigationPlanInline, SubTaskInline]
    
    actions = ['mark_completed', 'mark_failed', 'reset_to_pending']
    
    def status_badge(self, obj):
        """Color-coded status display"""
        colors = {
            'pending': 'orange',
            'running': 'blue',
            'paused': 'gray',
            'completed': 'green',
            'failed': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def duration_display(self, obj):
        """Calculate duration if investigation has started"""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{duration.days}d {hours}h {minutes}m"
        elif obj.started_at:
            return "In progress"
        return "-"
    duration_display.short_description = 'Duration'
    
    def mark_completed(self, request, queryset):
        """Bulk action to mark investigations as completed"""
        updated = queryset.update(status='completed', progress_percentage=100)
        self.message_user(request, f"{updated} investigation(s) marked as completed.")
    mark_completed.short_description = "Mark selected as Completed"
    
    def mark_failed(self, request, queryset):
        """Bulk action to mark investigations as failed"""
        updated = queryset.update(status='failed')
        self.message_user(request, f"{updated} investigation(s) marked as failed.")
    mark_failed.short_description = "Mark selected as Failed"
    
    def reset_to_pending(self, request, queryset):
        """Bulk action to reset investigations to pending"""
        updated = queryset.update(
            status='pending', 
            current_phase='planning',
            progress_percentage=0
        )
        self.message_user(request, f"{updated} investigation(s) reset to pending.")
    reset_to_pending.short_description = "Reset to Pending"
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'plan')
    
    class Media:
        css = {
            'all': ('admin/css/custom_investigation.css',)  # Optional custom styling
        }


@admin.register(InvestigationPlan)
class InvestigationPlanAdmin(admin.ModelAdmin):
    list_display = ('investigation', 'created_at', 'has_hypothesis', 'strategy_steps_count')
    search_fields = ('investigation__title', 'hypothesis')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    def has_hypothesis(self, obj):
        return bool(obj.hypothesis)
    has_hypothesis.boolean = True
    has_hypothesis.short_description = 'Has Hypothesis'
    
    def strategy_steps_count(self, obj):
        return len(obj.research_strategy) if isinstance(obj.research_strategy, list) else 0
    strategy_steps_count.short_description = 'Strategy Steps'


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    list_display = (
        'task_type', 
        'truncated_description', 
        'investigation_link',
        'status', 
        'confidence',
        'order',
        'started_at'
    )
    list_filter = ('task_type', 'status', 'investigation__title')
    search_fields = ('description', 'investigation__title')
    readonly_fields = ('id', 'started_at', 'completed_at')
    ordering = ('investigation', 'order')
    
    fieldsets = (
        ('Task Information', {
            'fields': ('investigation', 'parent_task', 'task_type', 'description', 'order')
        }),
        ('Status & Results', {
            'fields': ('status', 'confidence', 'result')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def truncated_description(self, obj):
        """Show first 60 characters of description"""
        return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description
    truncated_description.short_description = 'Description'
    
    def investigation_link(self, obj):
        """Link to parent investigation"""
        from django.urls import reverse
        url = reverse('admin:yourapp_investigation_change', args=[obj.investigation.id])
        return format_html('<a href="{}">{}</a>', url, obj.investigation.title)
    investigation_link.short_description = 'Investigation'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('investigation', 'parent_task')