"""
Django settings for the 8K Studio project.
"""

from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production-8kstudio')

DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'accounts',
    'studio',
    'billing',
    'siteeditor',
    'corepages',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'siteeditor.context_processors.site_config',
                'studio.context_processors.studio_globals',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:sign_in'
LOGIN_REDIRECT_URL = 'studio:dashboard'
LOGOUT_REDIRECT_URL = 'corepages:home'

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='8K Studio <noreply@8kstudio.app>')

# Every sign-up and login sends a notification email here with the user's
# details (name, email, plan, IP). Set to '' to disable.
ADMIN_NOTIFY_EMAIL = env('ADMIN_NOTIFY_EMAIL', default='rudrast251@gmail.com')

# ---------------------------------------------------------------------------
# Cloud storage (optional). When AWS_STORAGE_BUCKET_NAME is set, uploaded
# media is stored in S3-compatible object storage instead of local disk.
# ---------------------------------------------------------------------------
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
if AWS_STORAGE_BUCKET_NAME:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default=None)
    AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='auto')
    AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN', default=None)
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = env.bool('AWS_QUERYSTRING_AUTH', default=True)
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}
    INSTALLED_APPS += ['storages']

# ---------------------------------------------------------------------------
# 8K Studio: AI / processing configuration
# ---------------------------------------------------------------------------
REPLICATE_API_TOKEN = env('REPLICATE_API_TOKEN', default='')
REPLICATE_IMAGE_MODEL = env(
    'REPLICATE_IMAGE_MODEL',
    default='nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46a',
)
REPLICATE_VIDEO_MODEL = env(
    'REPLICATE_VIDEO_MODEL',
    default='lucataco/real-esrgan-video:c3e5a3b3e5d29ba6b9db63e9c15c7b31b8d3d1a5a6b0f9b34c1cc7b02a5c6e77',
)
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
ANTHROPIC_MODEL = env('ANTHROPIC_MODEL', default='claude-sonnet-4-5')

SITE_BASE_URL = env('SITE_BASE_URL', default='http://127.0.0.1:8000')
REPLICATE_WEBHOOK_SECRET = env('REPLICATE_WEBHOOK_SECRET', default='')

STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_PUBLISHABLE_KEY = env('STRIPE_PUBLISHABLE_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

# Manual UPI payments (India). When set, plan checkout shows a real scannable
# UPI QR code + UPI ID instead of the demo instant-grant flow. Payments are
# confirmed manually via the admin (Django has no way to verify a UPI
# transfer server-side without a payment-gateway business account), so the
# user submits an optional UTR/reference and an admin approves it from
# /admin/billing/paymentrequest/.
UPI_ID = env('UPI_ID', default='')
UPI_PAYEE_NAME = env('UPI_PAYEE_NAME', default='8K Studio')

DEMO_MODE = not bool(REPLICATE_API_TOKEN)

MAX_UPLOAD_SIZE_MB = env.int('MAX_UPLOAD_SIZE_MB', default=500)
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm']

DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
