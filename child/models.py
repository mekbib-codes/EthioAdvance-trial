from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from datetime import timedelta
import logging

from accounts.models import User

logger =  logging.getLogger('app')

class Child(models.Model):
    parent = models.ForeignKey(
        'parent.Parent',
        on_delete=models.CASCADE,
        related_name='children'
    )
    tutor = models.ForeignKey(
        'tutor.Tutor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    
    # Basic info
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=20, 
        choices=User.Gender.choices,  # Reuse the same Gender enum
        blank=True
    )
    
    # Education info
    grade_level = models.CharField(max_length=20)
    school = models.CharField(max_length=100)
    special_needs = models.TextField(blank=True)
    academic_interests = models.TextField(blank=True)

    avatar = models.ImageField(upload_to="child/profile/avatar/", null=True, blank=True)
    
    # Additional fields
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Child'
        verbose_name_plural = 'Children'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['grade_level']),
            models.Index(fields=['date_of_birth']),
        ]
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} (Parent: {self.parent})"
    
    def age(self):
        """Calculate age from date of birth"""
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    

class Status(models.Model):
    child = models.OneToOneField("child.Child", on_delete=models.CASCADE, related_name="status")
    sessions_summary = models.TextField(null=True, blank=True)
    strengths = models.TextField(null=True, blank=True)
    weaknesses = models.TextField(null=True, blank=True)
    improvement_notes = models.TextField(null=True, blank=True)
    mock_exam_graph = models.ImageField(upload_to="mock_exam_graphs/", null=True, blank=True)
    attendance_rate = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100.0)], null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Status for {self.child.get_full_name()} (Last updated: {self.updated_at.strftime('%Y-%m-%d')})"
    
    def get_queryset(self):
        return Child.objects.select_related('status').filter(parent=self.request.user)
    
    class Meta:
        verbose_name = 'Status'
        verbose_name_plural = 'Status'
        ordering = ['-updated_at']