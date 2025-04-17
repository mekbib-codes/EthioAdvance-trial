from django.contrib import admin
from .models import SessionRate, Payment

@admin.register(SessionRate)
class SessionRateAdmin(admin.ModelAdmin):
    list_display = ('current_hourly_rate', 'created_at', 'updated_at')  # Fields to display in the list view
    list_filter = ('updated_at',)  # Filter by updated_at
    search_fields = ('current_hourly_rate',)  # Search by hourly rate
    ordering = ('-updated_at',)  # Order by most recently updated

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('tx_ref', 'child', 'parent', 'amount', 'status', 'timestamp')  # Fields to display in the list view
    list_filter = ('status', 'timestamp')  # Filter by status and timestamp
    search_fields = ('tx_ref', 'child__name', 'parent__name')  # Search by transaction reference, child name, or parent name
    ordering = ('-timestamp',)  # Order by most recent payments
    autocomplete_fields = ('child', 'parent')  # Enable autocomplete for child and parent fields
    filter_horizontal = ('sessions',)  # Enable horizontal filter for sessions many-to-many field
