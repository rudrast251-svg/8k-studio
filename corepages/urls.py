from django.urls import path

from . import views

app_name = 'corepages'

urlpatterns = [
    path('', views.home, name='home'),
]
