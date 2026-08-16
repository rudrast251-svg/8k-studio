from django.conf import settings


def studio_globals(request):
    return {
        'demo_mode': settings.DEMO_MODE,
        'max_upload_mb': settings.MAX_UPLOAD_SIZE_MB,
    }
