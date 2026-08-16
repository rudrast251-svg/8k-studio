from .models import PaymentRequest


def pending_payments_count(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and user.is_staff:
        count = PaymentRequest.objects.filter(status=PaymentRequest.Status.PENDING).count()
        return {'pending_payments_count': count}
    return {'pending_payments_count': 0}
