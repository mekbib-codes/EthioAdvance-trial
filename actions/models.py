from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

class Notification(models.Model):
    """Core notification event with flexible verb-based actions"""
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications_created',
        help_text="User who triggered this notification"
    )
    verb = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Action verb (e.g., 'session.approved', 'payment.received')"
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of the main object this notification is about",
        null=True, blank=True
    )
    object_id = models.PositiveIntegerField(
        help_text="ID of the main object", null=True, blank=True
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    links = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_("Link"),
        help_text=_("URLs to redirect based on role to when this notification is clicked.")
    )

    class NotificationTypes(models.TextChoices):
        INFO = 'INFO', 'Info'
        SUCCESS = 'SUCCESS', 'Success'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'

    type = models.CharField(
        max_length=10,
        choices=NotificationTypes.choices,
        default=NotificationTypes.INFO,
        help_text="Type of notification"
    )

    # For child-related notifications
    child = models.ForeignKey(
        'child.Child',  # Replace with your actual Child model
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
        help_text="Related child (if applicable)"
    )
    
    # Additional context (e.g., payment amount, session details)
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context data in JSON format"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['verb']),  # For filtering by action type
        ]

    def __str__(self):
        return f"{self.verb} by {self.actor}"

class UserNotification(models.Model):
    """Delivery tracking for each user's notification instance"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='recipients'
    )
    is_read = models.BooleanField(
        default=False,
        db_index=True
    )
    delivered_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'notification')
        ordering = ['-delivered_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),  # Critical for inbox queries
            models.Index(fields=['delivered_at']),      # For chronological sorting
        ]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f"Notification for {self.user} ({'read' if self.is_read else 'unread'})"

class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        verbose_name=_("User"),
        help_text=_("The user who performed the action.")
    )
    action = models.CharField(
        max_length=500,
        verbose_name=_("Action"),
        help_text=_("Description of the action performed.")
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Content Type"),
        help_text=_("The type of the related object.",)
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Object ID"),
        help_text=_("The ID of the related object.",)
    )
    related_object = GenericForeignKey('content_type', 'object_id')
    
    link = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name=_("Link"),
        help_text=_("A URL to redirect to when this action is clicked.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Timestamp"),
        help_text=_("The time when the action was performed.")
    )

    class Meta:
        verbose_name = _("Activity Log")
        verbose_name_plural = _("Activity Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),  # For filtering by user and sorting by time
            models.Index(fields=['content_type', 'object_id']),  # For linking related objects
        ]

    def __str__(self):
        return f"{self.user} - {self.action} at {self.created_at}"