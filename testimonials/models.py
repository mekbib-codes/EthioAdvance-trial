from django.db import models
from parent.models import Parent
from django.utils.translation import gettext_lazy as _

class Testimonial(models.Model):
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name="testimonials",
        verbose_name=_("Parent"),
        help_text=_("The parent who provided the testimonial.")
    )
    text = models.TextField(
        verbose_name=_("Testimonial Text"),
        help_text=_("The content of the testimonial.")
    )
    show_testimonial = models.BooleanField(
        default=False,
        verbose_name=_("Show Testimonial"),
        help_text=_("Whether this testimonial should be displayed publicly.")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        help_text=_("The date and time when the testimonial was created.")
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Rating"),
        help_text=_("Optional rating provided by the parent (e.g., 1-5 stars).")
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured Testimonial"),
        help_text=_("Whether this testimonial should be highlighted as featured.")
    )

    class Meta:
        verbose_name = _("Testimonial")
        verbose_name_plural = _("Testimonials")
        ordering = ["-created_at"]  # Order by most recent first
        indexes = [
            models.Index(fields=["created_at"]),  # Index for fast retrieval
            models.Index(fields=["show_testimonial"]),  # Index for filtering displayed testimonials
        ]

    def __str__(self):
        return f"Testimonial by {self.parent.get_full_name()} ({self.created_at.strftime('%Y-%m-%d')})"


    def short_text(self):
        """Returns a shortened version of the testimonial text for display in admin."""
        return self.text[:50] + "..." if len(self.text) > 50 else self.text
    short_text.short_description = _("Short Testimonial Text")