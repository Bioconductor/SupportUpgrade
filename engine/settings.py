"""
Django settings for website project.

Generated by 'django-admin startproject' using Django 1.11.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os

from biostar.engine.log import LOGGING

SITE_ID = 1
SITE_DOMAIN = "localhost"
SITE_NAME = "Biostar Engine"
SITE_HEADER = '<i class="barcode icon"></i> Metagenomics Barcode Data Repository'

def join(*args):
    return os.path.abspath(os.path.join(*args))


ADMINS = [
    ("Admin User", "1@lvh.me")
]

ADMIN_GROUP_NAME = "Admins"

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(join(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '1@lvh.me'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
COMPRESS_ENABLED = True

# Application definition
PROTOCOL = "http"

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mailer',
    'compressor',
    'pagedown',
    'biostar.emailer',
    'biostar.accounts',
    'biostar.engine.apps.EngineConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'engine.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'string_if_invalid': "**MISSING**",
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.media',
                'django.contrib.messages.context_processors.messages',
                'engine.context.engine'
            ],
        },
    },
]

WSGI_APPLICATION = 'biostar.engine.wsgi.application'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASE_NAME = join(BASE_DIR, '..', 'export', 'database', 'engine.db')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_NAME,
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },

]

ALLOWED_HOSTS = ['www.lvh.me', 'localhost', '127.0.0.1']

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

MEDIA_ROOT = join(BASE_DIR, '..', 'export', 'media')

# The location of resusable data.
LOCAL_ROOT = join(BASE_DIR, '..', 'export', 'local')

MEDIA_URL = '/media/'
STATIC_URL = '/static/'
STATIC_ROOT = join(BASE_DIR, '..', 'export', 'static')
STATICFILES_DIRS = [
    join(BASE_DIR, "static"),
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

LOGGER_NAME = "biostar.engine"

# We are using django-mailer to store emails in the database.
# EMAIL_BACKEND = "mailer.backend.DbBackend"

# The email delivery engine.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
