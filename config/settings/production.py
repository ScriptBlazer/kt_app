import os

from config.settings.base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': int(os.getenv('POSTGRES_PORT', '5432')),
        'NAME': os.getenv('POSTGRES_DATABASE'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
    }
}

STATIC_ROOT = BASE_DIR / "staticfiles"