"""
Test settings for CI and local testing.
"""

import os

import dj_database_url

from .base import *  # noqa: F401, F403


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'test-secret-key-for-testing')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver', 'example.com']

CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000', 'https://example.com']


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# CI環境ではPostgreSQLを使用、ローカルテストではSQLiteを使用
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }


# ストレージバックエンドの設定（テストではファイルシステムを使用）
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = '/media/'


# Email設定（テスト環境ではロケーションメモリを使用）
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'test@example.com')


# テスト高速化のためのパスワードハッシャー
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

