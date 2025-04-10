from django.db import models
from accounts.models import User

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class ParentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.PARENT)
    
class Parent(User):

    objects = ParentManager()

    class Meta:
        proxy = True
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'

    @property
    def profile(self):
        return ParentProfile.objects.get_or_create(user=self)[0]

class ParentProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    company = models.ForeignKey(
        'company.Company',
        on_delete=models.PROTECT,
        related_name='parents'
    )
    occupation = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    preferred_communication = models.CharField(
        max_length=10,
        choices=[('EMAIL', 'Email'), ('PHONE', 'Phone'), ('SMS', 'SMS')],
        default='EMAIL'
    )

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"
    
    def clean(self):
        # Check if the user has the correct role
        if self.user.role != User.Role.PARENT:
            raise ValidationError(
                _('User must have the role of "Parent" to create a Parent Profile.'),
                code='invalid_role'
            )