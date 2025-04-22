from django.contrib import admin
from .models import Notification, UserNotification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor', 'verb', 'type', 'child', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('actor__email', 'verb', 'child__name')
    raw_id_fields = ('actor', 'child', 'content_type')
    readonly_fields = ('created_at',)
    list_select_related = ('actor', 'child')

    def get_queryset(self, request):
        """Optimize queries by selecting related fields."""
        return super().get_queryset(request).select_related('actor', 'child')

class UserNotificationInline(admin.TabularInline):
    model = UserNotification
    extra = 0
    readonly_fields = ('user', 'is_read', 'delivered_at', 'read_at')
    raw_id_fields = ('user',)

@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification', 'is_read', 'delivered_at', 'read_at')
    list_filter = ('is_read', 'delivered_at')
    search_fields = ('user__email', 'notification__verb')
    list_editable = ['is_read']
    raw_id_fields = ('user', 'notification')
    readonly_fields = ('delivered_at', 'read_at')
    list_select_related = ('user', 'notification')

    def get_queryset(self, request):
        """Optimize queries by selecting related fields."""
        return super().get_queryset(request).select_related('user', 'notification')
