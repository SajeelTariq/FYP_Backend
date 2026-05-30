"""
Django settings for competitor monitoring system.
"""
import os
import certifi
from pathlib import Path
from dotenv import load_dotenv

# Fix SSL certificate verification on Windows
os.environ.setdefault('SSL_CERT_FILE', certifi.where())
os.environ.setdefault('REQUESTS_CA_BUNDLE', certifi.where())

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-this-in-production')

# Firecrawl API Configuration
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', '')

# Apify API Configuration
APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN', '')
APIFY_COMPANY_ACTOR_ID = os.getenv('APIFY_COMPANY_ACTOR_ID', 'automation-lab~linkedin-company-scraper')
APIFY_JOBS_ACTOR_ID = os.getenv('APIFY_JOBS_ACTOR_ID', 'valig~linkedin-jobs-scraper')
APIFY_POSTS_ACTOR_ID = os.getenv('APIFY_POSTS_ACTOR_ID', 'harvestapi~linkedin-profile-posts')
APIFY_FB_POSTS_ACTOR_ID = os.getenv('APIFY_FB_POSTS_ACTOR_ID', 'automation-lab~facebook-posts-scraper')
APIFY_FB_PAGE_ACTOR_ID = os.getenv('APIFY_FB_PAGE_ACTOR_ID', 'tropical_quince~facebook-page-scraper')
APIFY_INSTAGRAM_ACTOR_ID = os.getenv('APIFY_INSTAGRAM_ACTOR_ID', 'apify~instagram-scraper')

# OpenRouter API Configuration (used by Agno agents)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# ChromaDB HTTP Server Configuration
CHROMA_HOST = os.getenv('CHROMA_HOST', '127.0.0.1')
CHROMA_PORT = int(os.getenv('CHROMA_PORT', '8001'))

# RAG Configuration
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '10'))
RAG_CACHE_TTL = int(os.getenv('RAG_CACHE_TTL', '7200'))  # seconds; 0 disables caching

# Maximum number of subpage links allowed per competitor
MAX_COMPETITOR_LINKS = int(os.getenv('MAX_COMPETITOR_LINKS', '500'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
    
    # Local apps
    'apps.accounts',
    'apps.monitoring',
    'apps.scraping',
    'apps.rag',
    'apps.analytics',
    'apps.social_media',
    'apps.reports',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database - PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'competitor_monitoring'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Milvus Vector Database Configuration
MILVUS_CONFIG = {
    'HOST': os.getenv('MILVUS_HOST', 'localhost'),
    'PORT': os.getenv('MILVUS_PORT', '19530'),
    'COLLECTION_NAME': os.getenv('MILVUS_COLLECTION', 'competitor_data'),
    'DIMENSION': int(os.getenv('MILVUS_DIMENSION', '768')),
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
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Settings
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:1500,http://127.0.0.1:1500'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Scripts Configuration
SCRIPTS_DIR = BASE_DIR / 'scripts'

# Financial Modeling Prep API
FMP_API_KEY = os.getenv('FMP_API_KEY', '')
FMP_BASE_URL = os.getenv('FMP_BASE_URL', 'https://financialmodelingprep.com/stable')

# Cache — LocMemCache by default; switch to django-redis in production:
# pip install django-redis, then set CACHE_BACKEND=django_redis.cache.RedisCache
CACHES = {
    'default': {
        'BACKEND': os.getenv(
            'CACHE_BACKEND',
            'django.core.cache.backends.locmem.LocMemCache',
        ),
        'LOCATION': os.getenv('CACHE_LOCATION', 'redis://127.0.0.1:6379/1'),
    }
}

# Email Configuration — SendGrid
EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
SENDGRID_SANDBOX_MODE_IN_DEBUG = False
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'TrackRival <noreply@trackrival.app>')