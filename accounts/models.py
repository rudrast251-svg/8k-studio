from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(
        'display name', max_length=150, unique=False, blank=True, validators=[],
        help_text='Your display name.',
    )
    company_name = models.CharField(max_length=120, blank=True)
    credits_balance = models.PositiveIntegerField(default=25)
    plan = models.ForeignKey(
        'billing.Plan', null=True, blank=True, on_delete=models.SET_NULL, related_name='subscribers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    @property
    def is_studio_admin(self):
        return self.is_staff or self.is_superuser
