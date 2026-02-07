# evidence/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.urls import reverse
from .models import Evidence, EvidenceEntityLink, EvidenceRelationshipLink


class CredibilityFilter(admin.SimpleListFilter):
    """Custom filter for evidence credibility"""
    title = 'credibility level'
    parameter_name = 'credibility'
    
    def lookups(self, request, model_admin):
        return [
            ('high', 'High Credibility'),
            ('medium', 'Medium Credibility'),
            ('low', 'Low Credibility'),
            ('unverified', 'Unverified'),
        ]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(source_credibility=self.value())
        return queryset


class HasFileFilter(admin.SimpleListFilter):
    """Filter evidence by file attachment"""
    title = 'file attachment'
    parameter_name = 'has_file'
    
    def lookups(self, request, model_admin):
        return [
            ('yes', 'Has File'),
            ('no', 'No File'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(file_path='')
        if self.value() == 'no':
            return queryset.filter(file_path='')
        return queryset


class EvidenceEntityLinkInline(admin.TabularInline):
    """Inline for entity links on Evidence admin"""
    model = EvidenceEntityLink
    extra = 1
    fields = ['entity', 'relevance', 'quote']
    autocomplete_fields = ['entity']
    verbose_name = "Linked Entity"
    verbose_name_plural = "Linked Entities"


class EvidenceRelationshipLinkInline(admin.TabularInline):
    """Inline for relationship links on Evidence admin"""
    model = EvidenceRelationshipLink
    extra = 1
    fields = ['relationship', 'supports', 'strength', 'quote']
    autocomplete_fields = ['relationship']
    verbose_name = "Linked Relationship"
    verbose_name_plural = "Linked Relationships"


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    """Admin interface for Evidence model"""
    
    list_display = [
        'title_with_icon',
        'investigation_link',
        'evidence_type_badge',
        'credibility_badge',
        'has_file_indicator',
        'has_source_url',
        'entity_count',
        'relationship_count',
        'created_at'
    ]
    
    list_filter = [
        'evidence_type',
        CredibilityFilter,
        HasFileFilter,
        'created_at',
        'investigation',
    ]
    
    search_fields = [
        'title',
        'content',
        'source_url',
        'investigation__title'
    ]
    
    autocomplete_fields = ['investigation', 'discovered_by_task']
    
    readonly_fields = [
        'id',
        'created_at',
        'entity_count',
        'relationship_count',
        'content_preview',
        'metadata_display',
        'file_info'
    ]
    
    fieldsets = (
        ('Evidence Information', {
            'fields': ('investigation', 'evidence_type', 'title', 'source_credibility')
        }),
        ('Content', {
            'fields': ('content', 'content_preview', 'source_url')
        }),
        ('File Attachment', {
            'fields': ('file_path', 'file_type', 'file_info'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'metadata_display'),
            'classes': ('collapse',)
        }),
        ('Discovery & Stats', {
            'fields': ('discovered_by_task', 'entity_count', 'relationship_count', 'created_at', 'id'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [EvidenceEntityLinkInline, EvidenceRelationshipLinkInline]
    
    actions = [
        'mark_high_credibility',
        'mark_medium_credibility',
        'mark_low_credibility',
        'mark_unverified',
    ]
    
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """Optimize queryset with counts"""
        qs = super().get_queryset(request)
        return qs.select_related('investigation', 'discovered_by_task').annotate(
            _entity_count=Count('entity_links', distinct=True),
            _relationship_count=Count('relationship_links', distinct=True)
        )
    
    def title_with_icon(self, obj):
        """Display title with type icon"""
        icons = {
            'document': '📄',
            'web_page': '🌐',
            'image': '🖼️',
            'video': '🎥',
            'testimony': '💬',
            'financial_record': '💰',
        }
        icon = icons.get(obj.evidence_type, '📎')
        
        return format_html(
            '{} <strong>{}</strong>',
            icon,
            obj.title
        )
    title_with_icon.short_description = 'Title'
    
    def investigation_link(self, obj):
        """Link to investigation"""
        if obj.investigation:
            url = reverse('admin:investigations_investigation_change', args=[obj.investigation.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.investigation.title
            )
        return '-'
    investigation_link.short_description = 'Investigation'
    
    def evidence_type_badge(self, obj):
        """Display evidence type as colored badge"""
        colors = {
            'document': '#007bff',
            'web_page': '#17a2b8',
            'image': '#28a745',
            'video': '#dc3545',
            'testimony': '#ffc107',
            'financial_record': '#6610f2',
        }
        color = colors.get(obj.evidence_type, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_evidence_type_display()
        )
    evidence_type_badge.short_description = 'Type'
    evidence_type_badge.admin_order_field = 'evidence_type'
    
    def credibility_badge(self, obj):
        """Display credibility as colored badge"""
        colors = {
            'high': '#28a745',
            'medium': '#ffc107',
            'low': '#dc3545',
            'unverified': '#6c757d',
        }
        color = colors.get(obj.source_credibility, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_source_credibility_display()
        )
    credibility_badge.short_description = 'Credibility'
    credibility_badge.admin_order_field = 'source_credibility'
    
    def has_file_indicator(self, obj):
        """Show if file is attached"""
        if obj.file_path:
            return format_html(
                '<a href="{}" target="_blank" style="color: green; font-weight: bold;">✓ File</a>',
                obj.file_path.url
            )
        return format_html('<span style="color: #999;">✗</span>')
    has_file_indicator.short_description = 'File'
    
    def has_source_url(self, obj):
        """Show if source URL exists"""
        if obj.source_url:
            return format_html(
                '<a href="{}" target="_blank" style="color: blue;">🔗 Link</a>',
                obj.source_url
            )
        return format_html('<span style="color: #999;">-</span>')
    has_source_url.short_description = 'URL'
    
    def entity_count(self, obj):
        """Count of linked entities"""
        count = getattr(obj, '_entity_count', 0)
        if count > 0:
            return format_html(
                '<span style="background: #e7f3ff; color: #0066cc; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: #999;">0</span>')
    entity_count.short_description = 'Entities'
    entity_count.admin_order_field = '_entity_count'
    
    def relationship_count(self, obj):
        """Count of linked relationships"""
        count = getattr(obj, '_relationship_count', 0)
        if count > 0:
            return format_html(
                '<span style="background: #fff3cd; color: #856404; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{}</span>',
                count
            )
        return format_html('<span style="color: #999;">0</span>')
    relationship_count.short_description = 'Relationships'
    relationship_count.admin_order_field = '_relationship_count'
    
    def content_preview(self, obj):
        """Preview of content"""
        if not obj.content:
            return '-'
        
        preview = obj.content[:300]
        if len(obj.content) > 300:
            preview += '...'
        
        return format_html(
            '<div style="background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; white-space: pre-wrap;">{}</div>',
            preview
        )
    content_preview.short_description = 'Content Preview'
    
    def metadata_display(self, obj):
        """Display metadata in formatted view"""
        if not obj.metadata:
            return '-'
        
        import json
        formatted = json.dumps(obj.metadata, indent=2)
        
        return format_html(
            '<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto;">{}</pre>',
            formatted
        )
    metadata_display.short_description = 'Metadata'
    
    def file_info(self, obj):
        """Display file information"""
        if not obj.file_path:
            return '-'
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
            '<strong>File:</strong> <a href="{}" target="_blank">{}</a><br>'
            '<strong>Type:</strong> {}'
            '</div>',
            obj.file_path.url,
            obj.file_path.name.split('/')[-1],
            obj.file_type or 'Unknown'
        )
    file_info.short_description = 'File Information'
    
    @admin.action(description='Mark as High Credibility')
    def mark_high_credibility(self, request, queryset):
        """Set credibility to high"""
        updated = queryset.update(source_credibility='high')
        self.message_user(request, f'{updated} evidence items marked as high credibility.')
    
    @admin.action(description='Mark as Medium Credibility')
    def mark_medium_credibility(self, request, queryset):
        """Set credibility to medium"""
        updated = queryset.update(source_credibility='medium')
        self.message_user(request, f'{updated} evidence items marked as medium credibility.')
    
    @admin.action(description='Mark as Low Credibility')
    def mark_low_credibility(self, request, queryset):
        """Set credibility to low"""
        updated = queryset.update(source_credibility='low')
        self.message_user(request, f'{updated} evidence items marked as low credibility.')
    
    @admin.action(description='Mark as Unverified')
    def mark_unverified(self, request, queryset):
        """Set credibility to unverified"""
        updated = queryset.update(source_credibility='unverified')
        self.message_user(request, f'{updated} evidence items marked as unverified.')


@admin.register(EvidenceEntityLink)
class EvidenceEntityLinkAdmin(admin.ModelAdmin):
    """Admin interface for EvidenceEntityLink model"""
    
    list_display = [
        'link_summary',
        'evidence_type',
        'entity_type',
        'relevance_badge',
        'has_quote',
        'evidence_credibility'
    ]
    
    list_filter = [
        'relevance',
        'evidence__evidence_type',
        'entity__entity_type',
        'evidence__source_credibility',
    ]
    
    search_fields = [
        'evidence__title',
        'entity__name',
        'quote'
    ]
    
    autocomplete_fields = ['evidence', 'entity']
    
    readonly_fields = ['id']
    
    fieldsets = (
        ('Link Information', {
            'fields': ('evidence', 'entity', 'relevance')
        }),
        ('Quote', {
            'fields': ('quote',)
        }),
        ('Metadata', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('evidence', 'entity')
    
    def link_summary(self, obj):
        """Display link as: Evidence → Entity"""
        return format_html(
            '<strong>{}</strong> <span style="color: #666;">→</span> <strong>{}</strong>',
            obj.evidence.title[:50],
            obj.entity.name
        )
    link_summary.short_description = 'Link'
    
    def evidence_type(self, obj):
        """Show evidence type"""
        return obj.evidence.get_evidence_type_display()
    evidence_type.short_description = 'Evidence Type'
    
    def entity_type(self, obj):
        """Show entity type"""
        return obj.entity.get_entity_type_display()
    entity_type.short_description = 'Entity Type'
    
    def relevance_badge(self, obj):
        """Display relevance as colored badge"""
        colors = {
            'primary': '#28a745',
            'secondary': '#ffc107',
            'mentioned': '#6c757d',
        }
        color = colors.get(obj.relevance, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_relevance_display()
        )
    relevance_badge.short_description = 'Relevance'
    relevance_badge.admin_order_field = 'relevance'
    
    def has_quote(self, obj):
        """Show if quote exists"""
        if obj.quote:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: #999;">✗</span>')
    has_quote.short_description = 'Quote'
    
    def evidence_credibility(self, obj):
        """Show evidence credibility"""
        return obj.evidence.get_source_credibility_display()
    evidence_credibility.short_description = 'Credibility'


@admin.register(EvidenceRelationshipLink)
class EvidenceRelationshipLinkAdmin(admin.ModelAdmin):
    """Admin interface for EvidenceRelationshipLink model"""
    
    list_display = [
        'link_summary',
        'relationship_type',
        'supports_indicator',
        'strength_bar',
        'has_quote',
        'evidence_credibility'
    ]
    
    list_filter = [
        'supports',
        'relationship__relationship_type',
        'evidence__evidence_type',
        'evidence__source_credibility',
    ]
    
    search_fields = [
        'evidence__title',
        'relationship__source_entity__name',
        'relationship__target_entity__name',
        'quote'
    ]
    
    autocomplete_fields = ['evidence', 'relationship']
    
    readonly_fields = ['id']
    
    fieldsets = (
        ('Link Information', {
            'fields': ('evidence', 'relationship', 'supports', 'strength')
        }),
        ('Quote', {
            'fields': ('quote',)
        }),
        ('Metadata', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_supporting', 'mark_contradicting', 'increase_strength', 'decrease_strength']
    
    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'evidence',
            'relationship',
            'relationship__source_entity',
            'relationship__target_entity'
        )
    
    def link_summary(self, obj):
        """Display link as: Evidence → Relationship"""
        rel_summary = f"{obj.relationship.source_entity.name} → {obj.relationship.target_entity.name}"
        return format_html(
            '<strong>{}</strong> <span style="color: #666;">→</span> {}',
            obj.evidence.title[:40],
            rel_summary
        )
    link_summary.short_description = 'Link'
    
    def relationship_type(self, obj):
        """Show relationship type"""
        return obj.relationship.get_relationship_type_display()
    relationship_type.short_description = 'Relationship Type'
    
    def supports_indicator(self, obj):
        """Show if supports or contradicts"""
        if obj.supports:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">✓ Supports</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">✗ Contradicts</span>'
        )
    supports_indicator.short_description = 'Effect'
    supports_indicator.admin_order_field = 'supports'
    
    def strength_bar(self, obj):
        """Display strength as progress bar"""
        width = int(obj.strength * 100)
        color = '#28a745' if obj.strength >= 0.7 else '#ffc107' if obj.strength >= 0.4 else '#dc3545'
        
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 11px; line-height: 20px;">{:.0%}</div>'
            '</div>',
            width,
            color,
            obj.strength
        )
    strength_bar.short_description = 'Strength'
    strength_bar.admin_order_field = 'strength'
    
    def has_quote(self, obj):
        """Show if quote exists"""
        if obj.quote:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: #999;">✗</span>')
    has_quote.short_description = 'Quote'
    
    def evidence_credibility(self, obj):
        """Show evidence credibility"""
        return obj.evidence.get_source_credibility_display()
    evidence_credibility.short_description = 'Credibility'
    
    @admin.action(description='Mark as Supporting')
    def mark_supporting(self, request, queryset):
        """Set links as supporting"""
        updated = queryset.update(supports=True)
        self.message_user(request, f'{updated} links marked as supporting.')
    
    @admin.action(description='Mark as Contradicting')
    def mark_contradicting(self, request, queryset):
        """Set links as contradicting"""
        updated = queryset.update(supports=False)
        self.message_user(request, f'{updated} links marked as contradicting.')
    
    @admin.action(description='Increase strength by 0.1')
    def increase_strength(self, request, queryset):
        """Increase strength for selected links"""
        count = 0
        for link in queryset:
            if link.strength < 1.0:
                link.strength = min(1.0, link.strength + 0.1)
                link.save()
                count += 1
        self.message_user(request, f'Increased strength for {count} links.')
    
    @admin.action(description='Decrease strength by 0.1')
    def decrease_strength(self, request, queryset):
        """Decrease strength for selected links"""
        count = 0
        for link in queryset:
            if link.strength > 0.0:
                link.strength = max(0.0, link.strength - 0.1)
                link.save()
                count += 1
        self.message_user(request, f'Decreased strength for {count} links.')