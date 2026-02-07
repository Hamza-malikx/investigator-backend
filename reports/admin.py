# reports/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.urls import reverse
from .models import Report


class ReportTypeFilter(admin.SimpleListFilter):
    """Custom filter for report types with counts"""
    title = 'report type'
    parameter_name = 'report_type'
    
    def lookups(self, request, model_admin):
        return [
            ('executive_summary', 'Executive Summary'),
            ('full_report', 'Full Report'),
            ('entity_profile', 'Entity Profile'),
        ]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(report_type=self.value())
        return queryset


class VersionFilter(admin.SimpleListFilter):
    """Filter reports by version status"""
    title = 'version status'
    parameter_name = 'version_status'
    
    def lookups(self, request, model_admin):
        return [
            ('latest', 'Latest Version Only'),
            ('v1', 'Version 1'),
            ('v2+', 'Version 2+'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'latest':
            # Get the latest version for each investigation+report_type combination
            from django.db.models import Max
            latest_versions = queryset.values('investigation', 'report_type').annotate(
                max_version=Max('version')
            )
            q_objects = Q()
            for item in latest_versions:
                q_objects |= Q(
                    investigation=item['investigation'],
                    report_type=item['report_type'],
                    version=item['max_version']
                )
            return queryset.filter(q_objects)
        if self.value() == 'v1':
            return queryset.filter(version=1)
        if self.value() == 'v2+':
            return queryset.filter(version__gte=2)
        return queryset


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin interface for Report model"""
    
    list_display = [
        'title_with_icon',
        'investigation_link',
        'report_type_badge',
        'format_badge',
        'version_badge',
        'has_file',
        'content_preview',
        'generated_at'
    ]
    
    list_filter = [
        ReportTypeFilter,
        'format',
        VersionFilter,
        'generated_at',
        'investigation',
    ]
    
    search_fields = ['title', 'content', 'investigation__title']
    
    autocomplete_fields = ['investigation']
    
    readonly_fields = [
        'id',
        'generated_at',
        'content_html_preview',
        'word_count',
        'investigation_details'
    ]
    
    fieldsets = (
        ('Report Information', {
            'fields': ('investigation', 'report_type', 'title')
        }),
        ('Content', {
            'fields': ('content', 'content_html_preview', 'word_count')
        }),
        ('Format & File', {
            'fields': ('format', 'file_path')
        }),
        ('Versioning & Metadata', {
            'fields': ('version', 'generated_at', 'id'),
            'classes': ('collapse',)
        }),
        ('Investigation Details', {
            'fields': ('investigation_details',),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'duplicate_report',
        'increment_version',
        'export_as_markdown',
        'mark_as_latest'
    ]
    
    date_hierarchy = 'generated_at'
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        qs = super().get_queryset(request)
        return qs.select_related('investigation')
    
    def title_with_icon(self, obj):
        """Display title with type icon"""
        icons = {
            'executive_summary': '📊',
            'full_report': '📄',
            'entity_profile': '👤',
        }
        icon = icons.get(obj.report_type, '📝')
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
    
    def report_type_badge(self, obj):
        """Display report type as colored badge"""
        colors = {
            'executive_summary': '#007bff',  # blue
            'full_report': '#28a745',  # green
            'entity_profile': '#ffc107',  # yellow
        }
        color = colors.get(obj.report_type, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_report_type_display()
        )
    report_type_badge.short_description = 'Type'
    
    def format_badge(self, obj):
        """Display format as badge"""
        colors = {
            'markdown': '#333',
            'pdf': '#dc3545',
            'html': '#17a2b8',
        }
        color = colors.get(obj.format, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.format
        )
    format_badge.short_description = 'Format'
    
    def version_badge(self, obj):
        """Display version with styling"""
        if obj.version == 1:
            color = '#28a745'
        elif obj.version <= 3:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 50%; font-weight: bold; font-size: 11px;">v{}</span>',
            color,
            obj.version
        )
    version_badge.short_description = 'Version'
    version_badge.admin_order_field = 'version'
    
    def has_file(self, obj):
        """Show if file is attached"""
        if obj.file_path:
            return format_html(
                '<a href="{}" target="_blank" style="color: green;">✓ File</a>',
                obj.file_path.url
            )
        return format_html('<span style="color: #999;">✗ No file</span>')
    has_file.short_description = 'File'
    
    def content_preview(self, obj):
        """Show content preview in list"""
        preview = obj.content[:100] if obj.content else ''
        if len(obj.content) > 100:
            preview += '...'
        return format_html(
            '<span style="color: #666; font-size: 11px;">{}</span>',
            preview
        )
    content_preview.short_description = 'Preview'
    
    def content_html_preview(self, obj):
        """Render content preview with markdown styling"""
        if not obj.content:
            return '-'
        
        # Simple markdown-like preview (you can enhance this with a proper markdown library)
        preview = obj.content[:500]
        if len(obj.content) > 500:
            preview += '\n\n...(truncated)'
        
        # Basic formatting
        preview = preview.replace('\n', '<br>')
        
        return format_html(
            '<div style="background: #f5f5f5; padding: 15px; border-radius: 5px; max-height: 400px; overflow-y: auto; font-family: monospace; font-size: 12px;">{}</div>',
            mark_safe(preview)
        )
    content_html_preview.short_description = 'Content Preview'
    
    def word_count(self, obj):
        """Count words in content"""
        if obj.content:
            return len(obj.content.split())
        return 0
    word_count.short_description = 'Word Count'
    
    def investigation_details(self, obj):
        """Show investigation details"""
        if not obj.investigation:
            return '-'
        
        inv = obj.investigation
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
            '<strong>Title:</strong> {}<br>'
            '<strong>Status:</strong> {}<br>'
            '<strong>Created:</strong> {}<br>'
            '<strong>User:</strong> {}'
            '</div>',
            inv.title,
            inv.get_status_display() if hasattr(inv, 'status') else 'N/A',
            inv.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(inv, 'created_at') else 'N/A',
            inv.user if hasattr(inv, 'user') else 'N/A'
        )
    investigation_details.short_description = 'Investigation Info'
    
    @admin.action(description='Duplicate selected reports')
    def duplicate_report(self, request, queryset):
        """Duplicate selected reports as new versions"""
        count = 0
        for report in queryset:
            report.pk = None
            report.id = None
            report.version += 1
            report.save()
            count += 1
        
        self.message_user(request, f'{count} reports duplicated successfully.')
    
    @admin.action(description='Increment version number')
    def increment_version(self, request, queryset):
        """Increment version for selected reports"""
        count = 0
        for report in queryset:
            report.version += 1
            report.save()
            count += 1
        
        self.message_user(request, f'Version incremented for {count} reports.')
    
    @admin.action(description='Export as Markdown (placeholder)')
    def export_as_markdown(self, request, queryset):
        """Export selected reports as markdown files"""
        # This is a placeholder - you would implement actual file export here
        count = queryset.count()
        self.message_user(
            request,
            f'Export functionality would process {count} reports. Implement file generation as needed.'
        )
    
    @admin.action(description='Mark as latest version')
    def mark_as_latest(self, request, queryset):
        """Set selected reports as the latest version for their type"""
        from django.db.models import Max
        
        count = 0
        for report in queryset:
            # Get the current max version for this investigation+type
            max_version = Report.objects.filter(
                investigation=report.investigation,
                report_type=report.report_type
            ).aggregate(Max('version'))['version__max']
            
            if max_version and report.version < max_version:
                report.version = max_version + 1
                report.save()
                count += 1
        
        self.message_user(request, f'{count} reports marked as latest version.')