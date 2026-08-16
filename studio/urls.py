from django.urls import path

from . import views

app_name = 'studio'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload, name='upload'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/status/', views.job_status, name='job_status'),
    path('jobs/<int:pk>/download/', views.job_download, name='job_download'),
    path('library/', views.library, name='library'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/mark-read/', views.notifications_mark_read, name='notifications_mark_read'),
]
