from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import SessionRate, Payment

@admin.register(SessionRate)
class SessionRateAdmin(admin.ModelAdmin):
    # Display fields in the list view
    list_display = ('id', 'current_hourly_rate', 'formatted_created_at', 'formatted_updated_at')
    list_filter = ('updated_at', 'created_at')
    search_fields = ('current_hourly_rate',)
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')

    # Custom formatted fields
    def formatted_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S')
    formatted_created_at.short_description = 'Created At'

    def formatted_updated_at(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M:%S')
    formatted_updated_at.short_description = 'Updated At'

    # Customize the add/edit form
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['current_hourly_rate'].help_text = "Enter the hourly rate for sessions (e.g., 400.00 ETB)."
        return form


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    # Display fields in the list view
    list_display = ('tx_ref', 'child_link', 'parent_link', 'amount', 'status', 'formatted_timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('tx_ref', 'child__first_name', 'child__last_name', 'parent__first_name', 'parent__last_name')
    ordering = ('-timestamp',)
    autocomplete_fields = ('child', 'parent')
    filter_horizontal = ('sessions',)
    readonly_fields = ('timestamp',)

    # Custom links for child and parent
    def child_link(self, obj):
        if obj.child:
            app_label = obj.child._meta.app_label
            model_name = obj.child._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.child.id])
            return format_html('<a href="{}">{}</a>', url, obj.child.get_full_name())
        return "-"
    child_link.short_description = 'Child'
    child_link.admin_order_field = 'child__first_name'

    def parent_link(self, obj):
        if obj.parent:
            app_label = obj.parent._meta.app_label
            model_name = obj.parent._meta.model_name
            url = reverse(f"admin:{app_label}_{model_name}_change", args=[obj.parent.id])
            return format_html('<a href="{}">{}</a>', url, obj.parent.get_full_name())
        return "-"
    parent_link.short_description = 'Parent'
    parent_link.admin_order_field = 'parent__first_name'

    # Custom formatted timestamp
    def formatted_timestamp(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    formatted_timestamp.short_description = 'Timestamp'

    # Customize the add/edit form
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['child'].help_text = "Select the child this payment is for."
        form.base_fields['parent'].help_text = "Select the parent making this payment."
        form.base_fields['amount'].help_text = "Enter the payment amount (e.g., 1200.00 ETB)."
        form.base_fields['status'].help_text = "Set the payment status (e.g., Pending, Success, Failed)."
        form.base_fields['sessions'].help_text = "Select the sessions covered by this payment."
        return form