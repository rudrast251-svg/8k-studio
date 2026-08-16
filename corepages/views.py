from django.conf import settings
from django.shortcuts import render

from billing.models import Plan
from studio.models import Asset


def home(request):
    plans = Plan.objects.filter(is_active=True)
    demo_assets = Asset.objects.filter(is_public_demo=True)[:4]
    return render(request, 'corepages/home.html', {
        'plans': plans,
        'demo_assets': demo_assets,
        'upi_enabled': bool(settings.UPI_ID),
    })
