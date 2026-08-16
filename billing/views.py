import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import CreditTransaction, PaymentRequest, Plan
from .services import adjust_credits, approve_payment_request, reject_payment_request
from .upi import build_upi_uri, render_qr_png

logger = logging.getLogger(__name__)


@login_required
def billing_home(request):
    plans = Plan.objects.filter(is_active=True)
    transactions = CreditTransaction.objects.filter(user=request.user)[:25]
    payment_requests = PaymentRequest.objects.filter(user=request.user)[:10]
    return render(request, 'billing/billing_home.html', {
        'plans': plans,
        'transactions': transactions,
        'payment_requests': payment_requests,
        'stripe_enabled': bool(settings.STRIPE_PUBLISHABLE_KEY),
        'upi_enabled': bool(settings.UPI_ID),
    })


@login_required
@require_POST
def checkout(request, slug):
    plan = get_object_or_404(Plan, slug=slug, is_active=True)

    if settings.STRIPE_SECRET_KEY and plan.stripe_price_id:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.create(
                mode='subscription',
                line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
                success_url=request.build_absolute_uri(reverse('billing:billing_home')) + '?upgraded=1',
                cancel_url=request.build_absolute_uri(reverse('billing:billing_home')),
                customer_email=request.user.email,
                client_reference_id=str(request.user.id),
                metadata={'plan_slug': plan.slug},
            )
            return redirect(session.url)
        except stripe.error.StripeError as exc:
            logger.exception('Stripe checkout failed')
            messages.error(request, f'Payment could not be started: {exc.user_message or exc}')
            return redirect('billing:billing_home')

    if settings.UPI_ID and plan.price_inr > 0:
        return redirect('billing:upi_checkout', slug=plan.slug)

    # Free plan, or no payment provider configured at all: grant instantly
    # so the upgrade flow is still fully clickable end-to-end, and say so.
    request.user.plan = plan
    request.user.save(update_fields=['plan'])
    adjust_credits(
        request.user, plan.monthly_credits, CreditTransaction.Reason.DEMO_TOPUP, job=None,
        note=f'Demo upgrade to {plan.name} (no payment processor configured)',
    )
    messages.success(
        request,
        f'Demo mode: connect Stripe or UPI to charge real payments. You have been switched to {plan.name} '
        f'and granted {plan.monthly_credits} credits.',
    )
    return redirect('billing:billing_home')


@login_required
def upi_checkout(request, slug):
    plan = get_object_or_404(Plan, slug=slug, is_active=True)
    if not settings.UPI_ID:
        raise Http404('UPI payments are not configured.')
    note = f'8K Studio {plan.name} plan'
    upi_uri = build_upi_uri(plan.price_inr, note)
    pending = PaymentRequest.objects.filter(
        user=request.user, plan=plan, status=PaymentRequest.Status.PENDING
    ).first()
    return render(request, 'billing/upi_checkout.html', {
        'plan': plan,
        'upi_id': settings.UPI_ID,
        'payee_name': settings.UPI_PAYEE_NAME,
        'upi_uri': upi_uri,
        'pending': pending,
    })


@login_required
def upi_qr_image(request, slug):
    plan = get_object_or_404(Plan, slug=slug, is_active=True)
    if not settings.UPI_ID:
        raise Http404('UPI payments are not configured.')
    note = f'8K Studio {plan.name} plan'
    png = render_qr_png(build_upi_uri(plan.price_inr, note))
    return HttpResponse(png, content_type='image/png')


@login_required
@require_POST
def upi_submit(request, slug):
    plan = get_object_or_404(Plan, slug=slug, is_active=True)
    if not settings.UPI_ID:
        raise Http404('UPI payments are not configured.')
    if PaymentRequest.objects.filter(user=request.user, plan=plan, status=PaymentRequest.Status.PENDING).exists():
        messages.info(request, 'You already have a payment pending review for this plan.')
        return redirect('billing:upi_checkout', slug=plan.slug)

    payment_request = PaymentRequest.objects.create(
        user=request.user, plan=plan, amount_inr=plan.price_inr,
        upi_ref=request.POST.get('upi_ref', '').strip()[:60],
    )

    from accounts.models import User
    from studio.models import Notification
    for admin in User.objects.filter(is_staff=True):
        Notification.objects.create(
            user=admin,
            message=f'💰 New payment to review: {request.user.email} claims Rs.{plan.price_inr:.0f} for {plan.name}.',
        )
    logger.info('New payment request #%s from %s for %s (Rs.%s)', payment_request.pk, request.user.email, plan.name, plan.price_inr)

    messages.success(
        request,
        f"Thanks! We've received your payment claim for Rs.{plan.price_inr:.0f}. "
        "An admin will verify it and activate your plan shortly.",
    )
    return redirect('billing:billing_home')


@staff_member_required
def pending_payments(request):
    """A simple, mobile-friendly one-tap review page for UPI payment claims
    — much faster to use than the full Django admin on a phone."""
    pending = PaymentRequest.objects.filter(status=PaymentRequest.Status.PENDING).select_related('user', 'plan')
    recent = PaymentRequest.objects.exclude(status=PaymentRequest.Status.PENDING).select_related('user', 'plan')[:15]
    return render(request, 'billing/pending_payments.html', {
        'pending': pending,
        'recent': recent,
    })


@staff_member_required
@require_POST
def approve_payment(request, pk):
    payment_request = get_object_or_404(PaymentRequest, pk=pk, status=PaymentRequest.Status.PENDING)
    approve_payment_request(payment_request, request.user)
    messages.success(request, f'Approved — {payment_request.user.email} now has the {payment_request.plan.name} plan.')
    return redirect('billing:pending_payments')


@staff_member_required
@require_POST
def reject_payment(request, pk):
    payment_request = get_object_or_404(PaymentRequest, pk=pk, status=PaymentRequest.Status.PENDING)
    reject_payment_request(payment_request, request.user)
    messages.info(request, f'Rejected payment claim from {payment_request.user.email}.')
    return redirect('billing:pending_payments')


@login_required
@require_POST
def demo_credit_grant(request):
    """Lets any signed-in user top up demo credits for testing without payment."""
    adjust_credits(request.user, 10, CreditTransaction.Reason.DEMO_TOPUP, note='Self-serve demo top-up')
    messages.success(request, '10 demo credits added to your account.')
    return redirect('billing:billing_home')


@csrf_exempt
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponseBadRequest('Stripe webhook is not configured.')
    import stripe
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest('Invalid signature')

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        from accounts.models import User
        user_id = session.get('client_reference_id')
        plan_slug = (session.get('metadata') or {}).get('plan_slug')
        user = User.objects.filter(pk=user_id).first()
        plan = Plan.objects.filter(slug=plan_slug).first()
        if user and plan:
            user.plan = plan
            user.save(update_fields=['plan'])
            adjust_credits(user, plan.monthly_credits, CreditTransaction.Reason.PURCHASE, note=f'Stripe checkout for {plan.name}')

    return HttpResponse(status=200)
