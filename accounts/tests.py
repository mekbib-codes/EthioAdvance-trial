from django.test import TestCase
from .models import User, OTP
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone

from datetime import timedelta

from .services.otp import OTPService

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

class OTPServiceTestCase(TestCase):
    def setUp(self):
        self.email = "test@example.com"
        self.purpose = OTP.Purpose.REGISTRATION
    
    def test_otp_generation(self):
        otp = OTPService.generate_otp(self.email, self.purpose)
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), settings.OTP_LENGTH)
    
    def test_otp_verification(self):
        otp = OTPService.generate_otp(self.email, self.purpose)
        is_valid, verified_otp = OTPService.verify_otp(
            self.email, 
            otp.otp_code, 
            self.purpose
        )
        self.assertTrue(is_valid)
        self.assertEqual(otp.id, verified_otp.id)
    
    def test_expired_otp(self):
        # Create OTP with explicit expiration in the past
        otp = OTP.objects.create(
            email=self.email,
            otp_code="123456",
            purpose=self.purpose,
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        # Refresh from database to ensure we have the actual state
        otp.refresh_from_db()
        # Verify is_valid() returns False
        self.assertFalse(otp.is_still_valid())
        # Verify verification fails
        is_valid, _ = OTPService.verify_otp(
            self.email, 
            otp.otp_code, 
            self.purpose
        )
        self.assertFalse(is_valid)
    
    def test_purge_expired_otps(self):
        # Create already expired OTP
        expired_otp = OTP.objects.create(
            email=self.email,
            otp_code="123456",
            purpose=self.purpose,
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        # Create valid OTP
        valid_otp = OTP.objects.create(
            email="valid@example.com",
            otp_code="654321",
            purpose=self.purpose
        )
        # Purge should only delete the expired one
        count = OTP.purge_expired_otps()
        self.assertEqual(count, 1)
        # Verify expired OTP was deleted
        with self.assertRaises(OTP.DoesNotExist):
            expired_otp.refresh_from_db()
        # Verify valid OTP still exists
        valid_otp.refresh_from_db()