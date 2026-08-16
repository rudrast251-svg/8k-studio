import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('studio.urls')),
    path('billing/', include('billing.urls')),
    path('site-editor/', include('siteeditor.urls')),
    path('', include('corepages.urls')),
]


# Serve locally-stored media (uploads, AI outputs, demo samples) regardless
# of DEBUG. This app has no S3/R2 storage configured by default, so without
# this route every image/video 404s in production. Django's own static()
# helper silently no-ops when DEBUG is False, which is why a naive fix using
# it doesn't work here — django.views.static.serve is used directly instead
# to bypass that. Harmless once real object storage
# (AWS_STORAGE_BUCKET_NAME) is configured, since file URLs then point at
# that bucket instead of hitting this route at all.
urlpatterns += [
    re_path(
        r'^%s(?P<path>.*)$' % re.escape(settings.MEDIA_URL.lstrip('/')),
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
