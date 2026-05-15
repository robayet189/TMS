"""
Django settings for mysite project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Production should set `DJANGO_SECRET_KEY` in environment variables.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-w0wtmb1*$w9*+olet#qff#t&42#bv-)8=a+7g%7-l=9&csu+rz')

# DEBUG can be enabled by setting DJANGO_DEBUG=1 or True in the environment
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

# Configure ALLOWED_HOSTS from environment (comma-separated) or default to your PA domain
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'zakirhosainabir.pythonanywhere.com').split(',')

# CSRF Settings for mobile app and hosting
CSRF_TRUSTED_ORIGINS = [
    'https://*.pythonanywhere.com',
    'http://*.pythonanywhere.com',
]
# Use secure cookies in production when served over HTTPS
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True').lower() in ('1', 'true', 'yes')
CSRF_COOKIE_HTTPONLY = os.environ.get('CSRF_COOKIE_HTTPONLY', 'True').lower() in ('1', 'true', 'yes')
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() in ('1', 'true', 'yes')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'channels',
    'myapp',
    'django.contrib.humanize', 
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
    'myapp.middleware.AdminRequiredMiddleware',
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'
ASGI_APPLICATION = 'mysite.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Use WhiteNoise to serve static files efficiently in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication
LOGIN_URL = '/login/'

# Email Configuration (Console backend for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Next Route <noreply@nextroute.com>'

# Channel Layers for WebSocket (Chat system)

DEFAULT_FROM_EMAIL = 'Next Route Transport <noreply@nextroute.com>'

# Make sure templates directory is included
import os
TEMPLATES[0]['DIRS'] = [os.path.join(BASE_DIR, 'templates')]


# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Next Route <noreply@nextroute.com>'


DEFAULT_FROM_EMAIL = 'Next Route <noreply@nextroute.com>'

# Redis for production (use in-memory for development)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# DRF Spectacular Settings for API Documentation
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Transport Management API',
    'DESCRIPTION': 'Complete API documentation for Transport Management System',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
DEFAULT_FROM_EMAIL = 'Next Route <noreply@nextroute.com>'

