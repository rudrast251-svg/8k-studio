from django.conf import settings
from django.db import models


class Plan(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=140, blank=True)
    price_usd = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    monthly_credits = models.PositiveIntegerField(default=25)
    max_resolution = models.CharField(max_length=20, default='4K')
    features = models.JSONField(default=list, blank=True)
    stripe_price_id = models.CharField(max_length=120, blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'price_usd']

    def __str__(self):
        return self.name


class CreditTransaction(models.Model):
    class Reason(models.TextChoices):
        SIGNUP_BONUS = 'signup_bonus', 'Signup bonus'
        MONTHLY_GRANT = 'monthly_grant', 'Monthly plan grant'
        DEMO_TOPUP = 'demo_topup', 'Demo top-up'
        PURCHASE = 'purchase', 'Purchase'
        JOB_CHARGE = 'job_charge', 'Job processing charge'
        JOB_REFUND = 'job_refund', 'Job refund (failed job)'
        ADMIN_ADJUSTMENT = 'admin_adjustment', 'Admin adjustment'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_transactions')
    amount = models.IntegerField(help_text='Positive to add credits, negative to deduct.')
    balance_after = models.IntegerField()
    reason = models.CharField(max_length=30, choices=Reason.choices)
    job = models.ForeignKey('studio.Job', null=True, blank=True, on_delete=models.SET_NULL, related_name='credit_transactions')
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} {self.amount:+d} ({self.reason})'
