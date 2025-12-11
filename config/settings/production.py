"""
Production settings.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

from .base import *  # noqa: F401, F403

# Load .env file
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS_ENV = os.getenv('ALLOWED_HOSTS')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(',')]

# CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS_ENV = os.getenv('CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_ENV.split(',')]


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Cloudflare R2設定
AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
AWS_S3_REGION_NAME = 'auto'


# ストレージバックエンドの設定
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# メディアファイルのURL（カスタムドメインを使う場合）
# MEDIA_URL = f'https://your-custom-domain.com/'
# またはR2の公開URLを使う場合
MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/'


# 本番環境用のセキュリティ設定
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True


# Email設定
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')
ANYMAIL = {
    "RESEND_API_KEY": os.environ.get('RESEND_API_KEY'),
}

