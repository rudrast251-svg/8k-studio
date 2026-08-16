from django.db import transaction

from .models import CreditTransaction


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
