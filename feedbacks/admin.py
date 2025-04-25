
from django.contrib import admin
from django.utils.html import format_html
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_text', 'created_at', 'status', 'status_badge')
    list_filter = ('rating', 'created_at')
    search_fields = ('text', 'user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('user', 'rating', 'created_at')
        }),
        ('Feedback Content', {
            'fields': ('text',),
            'classes': ('wide',),
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def short_text(self, obj):
        return obj.text[:75] + '...' if len(obj.text) > 75 else obj.text
    short_text.short_description = 'Feedback Preview'
    
    def status_badge(self, obj):
        if obj.rating is None:
            return format_html('<span style="color: #999;">No Rating</span>')
        elif obj.rating >= 4:
            return format_html('<span style="color: green; font-weight: bold;">★ {}</span>', obj.rating)
        elif obj.rating <= 2:
            return format_html('<span style="color: red; font-weight: bold;">★ {}</span>', obj.rating)
        else:
            return format_html('<span style="color: orange;">★ {}</span>', obj.rating)
    status_badge.short_description = 'Rating'
    status_badge.admin_order_field = 'rating'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')