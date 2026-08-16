from django.db import transaction
from django.utils import timezone

from .models import CreditTransaction, PaymentRequest


class InsufficientCreditsError(Exception):
    """Raised when a user does not have enough processing credits for a job."""


@transaction.atomic
def adjust_credits(user, amount, reason, job=None, note=''):
    """Atomically adjust a user's credit balance and record the ledger entry."""
    locked_user = user.__class__.objects.select_for_update().get(pk=user.pk)
    new_balance = locked_user.credits_balance + amount
    if new_balance < 0:
        raise InsufficientCreditsError(
            f'This action needs {abs(amount)} credits but you only have {locked_user.credits_balance}.'
        )
    locked_user.credits_balance = new_balance
    locked_user.save(update_fields=['credits_balance'])
    txn = CreditTransaction.objects.create(
        user=locked_user, amount=amount, balance_after=new_balance, reason=reason, job=job, note=note,
    )
    user.credits_balance = new_balance
    return txn


def charge_for_job(user, job):
    return adjust_credits(
        user, -job.credits_cost, CreditTransaction.Reason.JOB_CHARGE, job=job,
        note=f'Processing "{job.get_job_type_display()}" job #{job.id}',
    )


def refund_for_job(user, job):
    return adjust_credits(
        user, job.credits_cost, CreditTransaction.Reason.JOB_REFUND, job=job,
        note=f'Refund for failed job #{job.id}',
    )


@transaction.atomic
def approve_payment_request(payment_request: PaymentRequest, reviewer):
    if payment_request.status != PaymentRequest.Status.PENDING:
        return payment_request
    plan = payment_request.plan
    user = payment_request.user
    user.plan = plan
    user.save(update_fields=['plan'])
    adjust_credits(
        user, plan.monthly_credits, CreditTransaction.Reason.PURCHASE,
        note=f'UPI payment approved for {plan.name} (Rs.{payment_request.amount_inr})',
    )
    payment_request.status = PaymentRequest.Status.APPROVED
    payment_request.reviewed_by = reviewer
    payment_request.reviewed_at = timezone.now()
    payment_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    from studio.models import Notification
    Notification.objects.create(
        user=user,
        message=f'Payment of Rs.{payment_request.amount_inr} verified — you are now on the {plan.name} plan with {plan.monthly_credits} credits.',
    )
    return payment_request


def reject_payment_request(payment_request: PaymentRequest, reviewer):
    if payment_request.status != PaymentRequest.Status.PENDING:
        return payment_request
    payment_request.status = PaymentRequest.Status.REJECTED
    payment_request.reviewed_by = reviewer
    payment_request.reviewed_at = timezone.now()
    payment_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    from studio.models import Notification
    Notification.objects.create(
        user=payment_request.user,
        message=f"We couldn't verify your Rs.{payment_request.amount_inr} payment for {payment_request.plan.name}. Please contact support or try again.",
    )
    return payment_request
