from django.urls import path

from . import views

app_name = 'siteeditor'

urlpatterns = [
    path('', views.editor, name='editor'),
    path('reset/', views.reset, name='reset'),
]
