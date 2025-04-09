from django.test import TestCase
from .models import User
from django.contrib.auth import get_user_model

class UserManagerTest(TestCase):
    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            date_of_birth="2000-04-23",
        )
        self.assertTrue(admin.is_superuser)

class UserModelTest(TestCase):
    def test_user_creation(self):
        user = User.objects.create_user(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            date_of_birth="2000-01-01",
            role=User.Role.TUTOR
        )
        self.assertEqual(user.role, User.Role.TUTOR)

class AdminSiteTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            date_of_birth="2000-01-01",
            role=User.Role.TUTOR
        )
        self.client.force_login(self.admin)
