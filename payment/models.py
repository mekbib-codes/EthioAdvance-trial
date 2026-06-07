from django.db import models

from child.models import Child
from parent.models import Parent
from session.models import Session
from tutor.models import Tutor

class SessionRate(models.Model):
    rate_grade_1_4 = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    rate_grade_5_8 = models.DecimalField(max_digits=8, decimal_places=2, default=600)
    rate_grade_9_12 = models.DecimalField(max_digits=8, decimal_places=2, default=700)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_current_hourly_rate(self, child):
        grade = int(child.grade_level)

        if 1 <= grade <= 4:
            return self.rate_grade_1_4
        elif 5 <= grade <= 8:
            return self.rate_grade_5_8
        elif 9 <= grade <= 12:
            return self.rate_grade_9_12

        return self.rate_grade_5_8  # fallback

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['updated_at']),
        ]
  
class Payment(models.Model):

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    tx_ref = models.CharField(max_length=100, unique=True)
    child = models.ForeignKey(Child, on_delete=models.SET_NULL, blank=True, null=True, related_name='payments')
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, blank=True, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS.choices, default=STATUS.PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)
    sessions = models.ManyToManyField(Session, blank=True, related_name="payments")

    def __str__(self):
        return f"Payment {self.tx_ref} - {self.status} by {self.parent}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tx_ref']),
            models.Index(fields=['status']),
            models.Index(fields=['timestamp']),
        ]

class TutorPayRate(models.Model):
    rate_grade_1_4 = models.DecimalField(max_digits=8, decimal_places=2, default=350)
    rate_grade_5_8 = models.DecimalField(max_digits=8, decimal_places=2, default=450)
    rate_grade_9_12 = models.DecimalField(max_digits=8, decimal_places=2, default=550)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_current_hourly_rate(self, child):
        grade = int(child.grade_level)

        if 1 <= grade <= 4:
            return self.rate_grade_1_4
        elif 5 <= grade <= 8:
            return self.rate_grade_5_8
        elif 9 <= grade <= 12:
            return self.rate_grade_9_12

        return self.rate_grade_5_8  # fallback
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['updated_at']),
        ]

class TutorPayments(models.Model):

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    tx_ref = models.CharField(max_length=100, unique=True)
    child = models.ForeignKey(Child, on_delete=models.SET_NULL, blank=True, null=True, related_name="tutor_payments")
    tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, blank=True, null=True, related_name="tutor_payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS.choices, default=STATUS.PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)
    sessions = models.ManyToManyField(Session, blank=True, related_name="tutor_payments")

    def __str__(self):
        return f"Payment {self.tx_ref} - {self.status} to {self.tutor}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tx_ref']),
            models.Index(fields=['status']),
            models.Index(fields=['timestamp']),
        ]