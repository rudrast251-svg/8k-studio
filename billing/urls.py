from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.billing_home, name='billing_home'),
    path('pricing/', views.billing_home, name='pricing'),
    path('checkout/<slug:slug>/', views.checkout, name='checkout'),
    path('upi/<slug:slug>/', views.upi_checkout, name='upi_checkout'),
    path('upi/<slug:slug>/qr.png', views.upi_qr_image, name='upi_qr_image'),
    path('upi/<slug:slug>/submit/', views.upi_submit, name='upi_submit'),
    path('demo-credit-grant/', views.demo_credit_grant, name='demo_credit_grant'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
