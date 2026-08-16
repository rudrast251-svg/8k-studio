import logging

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.core.mail import send_mail
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


@receiver(user_logged_in)
def notify_admin_on_login(sender, request, user, **kwargs):
    if not settings.ADMIN_NOTIFY_EMAIL:
        return

    is_new_signup = (timezone.now() - user.created_at).total_seconds() < 15
    subject = f"{'🆕 New signup' if is_new_signup else '🔐 User login'} — {user.email}"
    body = (
        f"{'A new user just signed up' if is_new_signup else 'A user just logged in'} on 8K Studio.\n\n"
        f"Name: {user.username or '(not set)'}\n"
        f"Email: {user.email}\n"
        f"Company: {user.company_name or '(not set)'}\n"
        f"Plan: {user.plan.name if user.plan else 'None'}\n"
        f"Credits balance: {user.credits_balance}\n"
        f"Account created: {user.created_at:%Y-%m-%d %H:%M:%S UTC}\n"
        f"IP address: {_client_ip(request)}\n"
        f"Time: {timezone.now():%Y-%m-%d %H:%M:%S UTC}\n"
    )
    try:
        send_mail(
            subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_NOTIFY_EMAIL],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send login-notification email for user %s', user.pk)
