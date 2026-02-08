# entities/admin.py

from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from .models import Entity, Relationship


class RelationshipInline(admin.TabularInline):
    """Inline for managing relationships on the Entity admin page"""
    model = Relationship
    fk_name = 'source_entity'
    extra = 1
    fields = ['relationship_type', 'target_entity', 'confidence', 'strength', 'is_active', 'start_date', 'end_date']
    autocomplete_fields = ['target_entity']
    verbose_name = "Outgoing Relationship"
    verbose_name_plural = "Outgoing Relationships"


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    """Admin interface for Entity model"""
    
    list_display = [
        'name', 'entity_type', 'investigation_link', 'confidence_badge',
        'source_count', 'relationships_count', 'created_at'
    ]
    
    list_filter = [
        'entity_type',
        'created_at',
        'investigation',
    ]
    
    search_fields = ['name', 'aliases', 'description']
    
    autocomplete_fields = ['investigation', 'discovered_by_task']
    
    readonly_fields = ['id', 'created_at', 'relationships_count', 'evidence_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('investigation', 'entity_type', 'name', 'aliases', 'description')
        }),
        ('Confidence & Validation', {
            'fields': ('confidence', 'source_count')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Graph Visualization', {
            'fields': ('position_x', 'position_y'),
            'classes': ('collapse',)
        }),
        ('Discovery & Stats', {
            'fields': ('discovered_by_task', 'relationships_count', 'evidence_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [RelationshipInline]
    
    actions = ['mark_high_confidence', 'mark_low_confidence', 'reset_positions']
    
    def get_queryset(self, request):
        """Optimize queryset with relationship counts"""
        qs = super().get_queryset(request)
        return qs.annotate(
            _relationships_count=Count('outgoing_relationships') + Count('incoming_relationships'),
            _evidence_count=Count('evidence_links')
        )
    
    def investigation_link(self, obj):
        """Link to investigation"""
        if obj.investigation:
            url = f'/admin/investigations/investigation/{obj.investigation.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.investigation.title)
        return '-'
    investigation_link.short_description = 'Investigation'
    
    def confidence_badge(self, obj):
        """Display confidence as colored badge"""
        if obj.confidence >= 0.8:
            color = '#28a745'  # green
        elif obj.confidence >= 0.5:
            color = '#ffc107'  # yellow
        elif obj.confidence > 0:
            color = '#dc3545'  # red
        else:
            color = '#6c757d'  # gray
        
        # Format percentage separately to avoid format specifier issues
        percentage_text = f"{obj.confidence:.0%}"
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            percentage_text
        )
    confidence_badge.short_description = 'Confidence'
    confidence_badge.admin_order_field = 'confidence'
    
    def relationships_count(self, obj):
        """Count of all relationships"""
        return getattr(obj, '_relationships_count', 0)
    relationships_count.short_description = 'Relationships'
    relationships_count.admin_order_field = '_relationships_count'
    
    def evidence_count(self, obj):
        """Count of evidence links"""
        return getattr(obj, '_evidence_count', 0)
    evidence_count.short_description = 'Evidence'
    evidence_count.admin_order_field = '_evidence_count'
    
    @admin.action(description='Mark selected as high confidence (0.9)')
    def mark_high_confidence(self, request, queryset):
        """Set confidence to 0.9 for selected entities"""
        updated = queryset.update(confidence=0.9)
        self.message_user(request, f'{updated} entities marked as high confidence.')
    
    @admin.action(description='Mark selected as low confidence (0.3)')
    def mark_low_confidence(self, request, queryset):
        """Set confidence to 0.3 for selected entities"""
        updated = queryset.update(confidence=0.3)
        self.message_user(request, f'{updated} entities marked as low confidence.')
    
    @admin.action(description='Reset graph positions')
    def reset_positions(self, request, queryset):
        """Reset graph positions for selected entities"""
        updated = queryset.update(position_x=None, position_y=None)
        self.message_user(request, f'{updated} entities had their positions reset.')


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    """Admin interface for Relationship model"""
    
    list_display = [
        'relationship_summary', 'relationship_type', 'investigation_link',
        'confidence_badge', 'strength_bar', 'active_status', 'date_range', 'created_at'
    ]
    
    list_filter = [
        'relationship_type',
        'is_active',
        'created_at',
        'investigation',
    ]
    
    search_fields = [
        'source_entity__name',
        'target_entity__name',
        'description'
    ]
    
    autocomplete_fields = ['investigation', 'source_entity', 'target_entity', 'discovered_by_task']
    
    readonly_fields = ['id', 'created_at', 'evidence_count']
    
    fieldsets = (
        ('Relationship', {
            'fields': ('investigation', 'source_entity', 'target_entity', 'relationship_type', 'description')
        }),
        ('Confidence & Strength', {
            'fields': ('confidence', 'strength')
        }),
        ('Time Validity', {
            'fields': ('is_active', 'start_date', 'end_date')
        }),
        ('Discovery & Stats', {
            'fields': ('discovered_by_task', 'evidence_count', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_active', 'mark_inactive', 'increase_confidence', 'decrease_confidence']
    
    def get_queryset(self, request):
        """Optimize queryset with evidence counts"""
        qs = super().get_queryset(request)
        return qs.select_related('source_entity', 'target_entity', 'investigation').annotate(
            _evidence_count=Count('evidence_links')
        )
    
    def relationship_summary(self, obj):
        """Display relationship as: Source -> Type -> Target"""
        return format_html(
            '<strong>{}</strong> <span style="color: #666;">→</span> {} <span style="color: #666;">→</span> <strong>{}</strong>',
            obj.source_entity.name,
            obj.get_relationship_type_display(),
            obj.target_entity.name
        )
    relationship_summary.short_description = 'Relationship'
    
    def investigation_link(self, obj):
        """Link to investigation"""
        if obj.investigation:
            url = f'/admin/investigations/investigation/{obj.investigation.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.investigation.title)
        return '-'
    investigation_link.short_description = 'Investigation'
    
    def confidence_badge(self, obj):
        """Display confidence as colored badge"""
        if obj.confidence >= 0.8:
            color = '#28a745'
        elif obj.confidence >= 0.5:
            color = '#ffc107'
        elif obj.confidence > 0:
            color = '#dc3545'
        else:
            color = '#6c757d'
        
        # Format percentage separately to avoid format specifier issues
        percentage_text = f"{obj.confidence:.0%}"
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            percentage_text
        )
    confidence_badge.short_description = 'Confidence'
    confidence_badge.admin_order_field = 'confidence'
    
    def strength_bar(self, obj):
        """Display strength as progress bar"""
        width = int(obj.strength * 100)
        color = '#007bff' if obj.strength >= 0.5 else '#6c757d'
        
        # Format percentage separately to avoid format specifier issues
        percentage_text = f"{obj.strength:.0%}"
        
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 11px; line-height: 20px;">{}</div>'
            '</div>',
            width,
            color,
            percentage_text
        )
    strength_bar.short_description = 'Strength'
    strength_bar.admin_order_field = 'strength'
    
    def active_status(self, obj):
        """Display active status with icon"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    active_status.short_description = 'Status'
    active_status.admin_order_field = 'is_active'
    
    def date_range(self, obj):
        """Display date range if available"""
        if obj.start_date or obj.end_date:
            start = obj.start_date.strftime('%Y-%m-%d') if obj.start_date else '?'
            end = obj.end_date.strftime('%Y-%m-%d') if obj.end_date else '?'
            return f'{start} → {end}'
        return '-'
    date_range.short_description = 'Date Range'
    
    def evidence_count(self, obj):
        """Count of evidence links"""
        return getattr(obj, '_evidence_count', 0)
    evidence_count.short_description = 'Evidence'
    evidence_count.admin_order_field = '_evidence_count'
    
    @admin.action(description='Mark selected as active')
    def mark_active(self, request, queryset):
        """Set relationships as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} relationships marked as active.')
    
    @admin.action(description='Mark selected as inactive')
    def mark_inactive(self, request, queryset):
        """Set relationships as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} relationships marked as inactive.')
    
    @admin.action(description='Increase confidence by 0.1')
    def increase_confidence(self, request, queryset):
        """Increase confidence for selected relationships"""
        count = 0
        for relationship in queryset:
            if relationship.confidence < 1.0:
                relationship.confidence = min(1.0, relationship.confidence + 0.1)
                relationship.save()
                count += 1
        self.message_user(request, f'Increased confidence for {count} relationships.')
    
    @admin.action(description='Decrease confidence by 0.1')
    def decrease_confidence(self, request, queryset):
        """Decrease confidence for selected relationships"""
        count = 0
        for relationship in queryset:
            if relationship.confidence > 0.0:
                relationship.confidence = max(0.0, relationship.confidence - 0.1)
                relationship.save()
                count += 1
        self.message_user(request, f'Decreased confidence for {count} relationships.')