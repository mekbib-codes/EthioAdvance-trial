from django.db import models

from child.models import Child
from parent.models import Parent
from session.models import Session

class SessionRate(models.Model):
    current_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=400.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rate: {self.current_hourly_rate} ETB (updated {self.updated_at})"
  
class Payment(models.Model):

    class STATUS(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    tx_ref = models.CharField(max_length=100, unique=True)
    child = models.ForeignKey(Child, on_delete=models.SET_NULL, blank=True, null=True)
    parent = models.ForeignKey(Parent, on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS.choices, default=STATUS.PENDING)
    timestamp = models.DateTimeField(auto_now_add=True)
    sessions = models.ManyToManyField(Session, blank=True, related_name="payments")

    def __str__(self):
        return f"Payment {self.tx_ref} - {self.status}"