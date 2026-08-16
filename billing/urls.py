from django.urls import path

from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.billing_home, name='billing_home'),
    path('pricing/', views.billing_home, name='pricing'),
    path('checkout/<slug:slug>/', views.checkout, name='checkout'),
    path('demo-credit-grant/', views.demo_credit_grant, name='demo_credit_grant'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
