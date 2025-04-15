from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Session

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    # Display fields in the list view
    list_display = ('id', 'child_link', 'tutor_link', 'session_subject', 'status', 'formatted_duration', 'is_paid', 'created_at')
    list_filter = ('status', 'is_paid', 'created_at', 'updated_at')
    search_fields = ('child__first_name', 'child__last_name', 'tutor__first_name', 'tutor__last_name', 'session_subject')
    list_editable = ('status', 'is_paid')
    list_per_page = 25
    autocomplete_fields = ['child', 'tutor']

    # Group fields in the edit view
    fieldsets = (
        ('Session Details', {
            'fields': (
                ('child', 'tutor'),
                ('start_time', 'end_time'),
                'duration',
                'session_subject',
                'session_summary',
            )
        }),
        ('Status & Payment', {
            'fields': (
                'status',
                'is_paid',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    # Make certain fields read-only
    readonly_fields = ('duration', 'created_at', 'updated_at')

    # Custom link to the child in the admin
    def child_link(self, obj):
        if obj.child:
            app_label = obj.child._meta.app_label
            model_name = obj.child._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.child.id])
            return format_html('<a href="{}">{}</a>', url, obj.child.get_full_name())
        return "-"
    child_link.short_description = 'Child'
    child_link.admin_order_field = 'child__first_name'

    # Custom link to the tutor in the admin
    def tutor_link(self, obj):
        if obj.tutor:
            app_label = obj.tutor._meta.app_label
            model_name = obj.tutor._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.tutor.id])
            return format_html('<a href="{}">{}</a>', url, obj.tutor.get_full_name())
        return "-"
    tutor_link.short_description = 'Tutor'
    tutor_link.admin_order_field = 'tutor__first_name'

    # Display formatted duration in the list view
    def formatted_duration(self, obj):
        if obj.duration:
            total_minutes = int(obj.duration.total_seconds() / 60)
            hours, minutes = divmod(total_minutes, 60)
            if hours and minutes:
                return f"{hours} hr{'s' if hours > 1 else ''} {minutes} min{'s' if minutes > 1 else ''}"
            elif hours:
                return f"{hours} hr{'s' if hours > 1 else ''}"
            else:
                return f"{minutes} min{'s' if minutes > 1 else ''}"
        return "N/A"
    formatted_duration.short_description = 'Duration'

    # Customize the add/edit form to show help texts
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['child'].help_text = "Select the child this session is for."
        form.base_fields['tutor'].help_text = "Select the tutor conducting this session."
        form.base_fields['start_time'].help_text = "Enter the session start time (e.g., 14:00)."
        form.base_fields['end_time'].help_text = "Enter the session end time (e.g., 15:30)."
        form.base_fields['session_subject'].help_text = "Enter the subject of the session."
        form.base_fields['session_summary'].help_text = "Provide a brief summary of the session."
        return form