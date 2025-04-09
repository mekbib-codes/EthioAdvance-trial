from django.db import models
from accounts.models import User

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class ChildManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role=User.Role.CHILD)
    
class Child(User):

    objects = ChildManager()

    class Meta:
        proxy = True
        verbose_name = 'Child'
        verbose_name_plural = 'Children'

    @property
    def profile(self):
        return ChildProfile.objects.get_or_create(user=self)[0]

class ChildProfile(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='child_profile'
    )
    parent = models.ForeignKey(
        'parent.Parent',
        on_delete=models.PROTECT,
        related_name='children'
    )
    tutor = models.ForeignKey(
        'tutor.Tutor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    grade_level = models.CharField(max_length=20)
    school = models.CharField(max_length=100)
    special_needs = models.TextField(blank=True)
    academic_interests = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"

    def clean(self):
        # Check if the user has the correct role
        if self.user.role != User.Role.CHILD:
            raise ValidationError(
                _('User must have the role of "Child" to create a Child Profile.'),
                code='invalid_role'
            )