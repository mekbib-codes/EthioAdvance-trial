from django.db import models
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError

class Session(models.Model):
    tutor = models.ForeignKey("tutor.Tutor", on_delete=models.CASCADE, related_name="sessions")
    child = models.ForeignKey("child.Child", on_delete=models.CASCADE, related_name="sessions")
    
    start_time = models.TimeField()  # Changed to TimeField
    end_time = models.TimeField() 
    duration = models.DurationField(null=True, blank=True)

    session_subject = models.CharField(max_length=255)
    session_summary = models.TextField()

    class Status(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PENDING = "pending", "Pending"
        

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # The field below is used to indicate whether the session has been paid for or not.
    
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")
    
    def save(self, *args, **kwargs):
        """Automatically calculates and saves session duration before saving the model."""
        if self.start_time and self.end_time:
            today = datetime.today().date()
            start_dt = datetime.combine(today, self.start_time)
            end_dt = datetime.combine(today, self.end_time)

            # Handle cases where session ends after midnight
            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            self.duration = end_dt - start_dt  # Store as timedelta

        super().save(*args, **kwargs)  # Save the model

    def formatted_duration(self):
        if not self.duration:
            return "N/A"
        
        total_minutes = int(self.duration.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)

        if hours and minutes:
            return f"{hours} hr{'s' if hours > 1 else ''} {minutes} min{'s' if minutes > 1 else ''}"
        elif hours:
            return f"{hours} hr{'s' if hours > 1 else ''}"
        else:
            return f"{minutes} min{'s' if minutes > 1 else ''}"

    def __str__(self):
        return f"Session ({self.tutor} - {self.child}) - {self.get_status_display()} at {self.start_time.strftime('%H:%M')} for {self.duration}"



