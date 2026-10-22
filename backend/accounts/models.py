import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError("Phone is required")
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", "ADMIN")
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = [
        ("CUSTOMER", "Customer"),
        ("COUNTER_STAFF", "Counter staff"),
        ("MANAGER", "Theatre manager"),
        ("ADMIN", "Platform admin"),
    ]

    phone = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=20, choices=ROLES, default="CUSTOMER")
    strike_count = models.PositiveSmallIntegerField(default=0)
    blocked_until = models.DateTimeField(null=True, blank=True)

    # For counter staff / managers: the theatre they work at
    theatre = models.ForeignKey(
        "theatres.Theatre", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="staff", help_text="For counter staff / managers")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "phone"
    objects = UserManager()

    def __str__(self):
        return self.phone


class OTP(models.Model):
    phone = models.CharField(max_length=15, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)

    @staticmethod
    def generate(phone):
        code = f"{secrets.randbelow(1_000_000):06d}"   # cryptographically secure
        return OTP.objects.create(phone=phone, code=code)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)