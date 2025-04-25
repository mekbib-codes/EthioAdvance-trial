from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Feedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedbacks",
        verbose_name=_("User"),
        help_text=_("The user who provided the feedback.")
    )
    text = models.TextField(
        verbose_name=_("Feedback Text"),
        help_text=_("The content of the feedback.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("The date and time when the feedback was created.")
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Rating"),
        help_text=_("Optional rating provided by the user (e.g., 1-5 stars).")
    )

    class FeedbackStatus(models.TextChoices):
        OPEN = 'open', _('Open')
        REVIEWED = 'reviewed', _('Reviewed')
        RESOLVED = 'resolved', _('Resolved')

    status = models.CharField(
        max_length=10,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.OPEN,
        verbose_name=_("Status")
    )

    class Meta:
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedback")
        ordering = ["-created_at"]  # Order by most recent first
        indexes = [
            models.Index(fields=["created_at"]),  # Index for fast retrieval
        ]

    def __str__(self):
        return f"Testimonial by {self.user.get_full_name()} ({self.created_at.strftime('%Y-%m-%d')})"


    def short_text(self):
        """Returns a shortened version of the feedback text for display in admin."""
        return self.text[:50] + "..." if len(self.text) > 50 else self.text
    short_text.short_description = _("Short Feedback Text")