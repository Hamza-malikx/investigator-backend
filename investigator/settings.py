import os
from pathlib import Path
from urllib.parse import urlparse
from datetime import timedelta
from dotenv import load_dotenv
# from celery.schedules import crontab

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-)pm%x3_wer7e--ltq1h^6r27m(!95%(=7!c$11yss^^exy2g6_')
DEBUG = os.environ.get('DEBUG', '0') == '1'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',  # Added for JWT
    'rest_framework_simplejwt.token_blacklist',  # Added for token blacklisting
    'corsheaders',
    'django_filters',
    # 'accounts',
    # 'cities',
    # "boosts",
    # "reviews",
    # "votes",
    # "moderation",
    # "audit_logs",
    # 'telegram',
    # 'notifications',
    # 'django_celery_beat',
    # 'django_celery_results',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "investigator.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "investigator.wsgi.application"


# Database Configuration - PostgreSQL for both development and production
if os.environ.get('DATABASE_URL'):
    # Parse DATABASE_URL for production
    db_url = urlparse(os.environ.get('DATABASE_URL'))
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_url.path[1:],
            'USER': db_url.username,
            'PASSWORD': db_url.password,
            'HOST': db_url.hostname,
            'PORT': db_url.port or 5432,
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }
else:
    # Development database (PostgreSQL with environment variables)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'memcoin_dev'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60 if not DEBUG else 0,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

# Custom User Model
# AUTH_USER_MODEL = 'authentication.User'
# AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'


# Static files storage (Production)
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Changed for public API
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ]
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': True,  # Generate new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,  # Blacklist old refresh token after rotation
    'UPDATE_LAST_LOGIN': True,  # Update last_login field on token generation
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
    
    # Custom claims
    'TOKEN_OBTAIN_SERIALIZER': 'accounts.serializers.CustomTokenObtainPairSerializer',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_CREDENTIALS=True
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://185.247.226.219').split(',')
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF cookie
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-site requests
CSRF_COOKIE_SECURE = False  # For HTTP (set True for HTTPS)
# Session Configuration
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = False  # For HTTP (set True for HTTPS)
SESSION_COOKIE_HTTPONLY = True
# Security Settings (Production)
# if not DEBUG:
#     SECURE_BROWSER_XSS_FILTER = True
#     SECURE_CONTENT_TYPE_NOSNIFF = True
#     SECURE_HSTS_INCLUDE_SUBDOMAINS = False # Set to True if you want to include subdomains
#     SECURE_HSTS_SECONDS = 31536000
#     SECURE_REDIRECT_EXEMPT = []
#     SECURE_SSL_REDIRECT = False  # Set to True if using HTTPS
#     SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
#     CSRF_COOKIE_SECURE = False # Set to True if using HTTPS
#     X_FRAME_OPTIONS = 'DENY'



# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
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
            'filename': 'django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'scraping': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'telegram': {'handlers': ['console'], 'level': 'INFO'},
    },
}

# Health check endpoint
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percent
    'MEMORY_MIN': 100,     # in MB
}
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')
# Add caching for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://redis:6379/1'),
        # 'OPTIONS': {
        #     'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        # }
    }
}

# Session configuration for analytics
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 86400 * 30  # 30 days

# # =============================================================================
# # CELERY CONFIGURATION
# # =============================================================================

# # Celery Configuration Options
# CELERY_BROKER_URL = f'{REDIS_URL}/0'
# CELERY_RESULT_BACKEND = f'{REDIS_URL}/0'

# # Celery Task Configuration
# CELERY_TASK_ALWAYS_EAGER = DEBUG  # Run tasks synchronously in development
# CELERY_TASK_EAGER_PROPAGATES = DEBUG
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TIMEZONE = TIME_ZONE
# CELERY_ENABLE_UTC = True

# # Task execution settings
# CELERY_TASK_SOFT_TIME_LIMIT = 60 * 30  # 30 minutes
# CELERY_TASK_TIME_LIMIT = 60 * 35      # 35 minutes (hard limit)
# CELERY_TASK_MAX_RETRIES = 3
# CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minute

# # Worker settings
# CELERY_WORKER_CONCURRENCY = os.environ.get('CELERY_WORKER_CONCURRENCY', 4)
# CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
# CELERY_WORKER_DISABLE_RATE_LIMITS = False
# CELERY_WORKER_PREFETCH_MULTIPLIER = 4

# # Queue configuration
# CELERY_TASK_ROUTES = {
#     'accounts.tasks.*': {'queue': 'default'},
#     'scraping.tasks.*': {'queue': 'scraping'},
#     'trend.tasks.*': {'queue': 'trends'},
#     'boosts.tasks.*': {'queue': 'default'},
#     'telegram.*': {'queue': 'celery'},
#     '*': {'queue': 'default'}
# }

# # Celery Beat configuration (for scheduled tasks)
# CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# # CELERY_BEAT_SCHEDULE = {
# #     # 'expire-boost-statuses': {
# #     #     'task': 'boosts.expire_all_boosts',
# #     #     'schedule': crontab(minute='*/10'),
# #     #     'options': {
# #     #         'expires': 600,
# #     #     }
# #     # },
# #     'expire-all-boosts': {
# #         'task': 'boosts.expire_all_boosts',
# #         'schedule': crontab(minute='*/10'),  # Every 10 minutes
# #     },
# #     'process-auto-bumps': {
# #         'task': 'boosts.process_auto_bumps',  
# #         'schedule': crontab(minute='*/5'),  # Every 5 minutes
# #     },
# # }
# CELERY_BEAT_SCHEDULE = {
#     # Existing boost tasks
#     'expire-all-boosts': {
#         'task': 'boosts.expire_all_boosts',
#         'schedule': crontab(minute='*/10'),  # Every 10 minutes
#     },
#     'process-auto-bumps': {
#         'task': 'boosts.process_auto_bumps',  
#         'schedule': crontab(minute='*/5'),  # Every 5 minutes
#     },
    
#     # New payment tasks
#     'expire-pending-payments': {
#         'task': 'boosts.expire_pending_payments',
#         'schedule': crontab(minute='*/5'),  # Every 5 minutes
#         'options': {
#             'expires': 300,  # Task expires after 5 minutes
#         }
#     },
#     'check-pending-payments': {
#         'task': 'boosts.check_pending_payments',
#         'schedule': crontab(minute='*/10'),  # Every 10 minutes
#         'options': {
#             'expires': 600,  # Task expires after 10 minutes
#         }
#     },
#     'expire-active-boosts': {
#         'task': 'boosts.expire_active_boosts',
#         'schedule': crontab(minute=0),  # Every hour
#         'options': {
#             'expires': 3600,  # Task expires after 1 hour
#         }
#     },
#     'cleanup-old-webhooks': {
#         'task': 'boosts.cleanup_old_webhooks',
#         'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
#         'options': {
#             'expires': 86400,  # Task expires after 1 day
#         }
#     },
#     # Weekly Top 5 leaderboard (Every Sunday at 9 AM)
#     'generate-weekly-top5': {
#         'task': 'telegram.generate_weekly_top5',
#         'schedule': crontab(day_of_week=0, hour=9, minute=0),
#         'options': {
#             'expires': 3600,
#         }
#     },
    
#     # Check trial expiry (Daily at 8 AM)
#     'check-trial-expiry': {
#         'task': 'telegram.check_trial_expiry',
#         'schedule': crontab(hour=8, minute=0),
#         'options': {
#             'expires': 3600,
#         }
#     },
    
#     # Cleanup old messages (Daily at 3 AM)
#     'cleanup-old-telegram-messages': {
#         'task': 'telegram.cleanup_old_messages',
#         'schedule': crontab(hour=3, minute=0),
#         'options': {
#             'expires': 3600,
#         }
#     },
    
#     # Retry failed messages (Every hour)
#     'retry-failed-telegram-messages': {
#         'task': 'telegram.retry_failed_messages',
#         'schedule': crontab(minute=0),
#         'options': {
#             'expires': 3600,
#         }
#     },
    
#     # Update message stats (Daily at midnight)
#     'update-telegram-message-stats': {
#         'task': 'telegram.update_message_stats',
#         'schedule': crontab(hour=0, minute=0),
#         'options': {
#             'expires': 3600,
#         }
#     },

#     'telegram-bot-updates': {
#         'task': 'telegram.process_bot_updates',
#         'schedule': 30.0,
#     },
# }

# # Result backend settings
# CELERY_RESULT_EXPIRES = 60 * 60 * 24  # 24 hours

# # Error handling
# CELERY_TASK_REJECT_ON_WORKER_LOST = True
# CELERY_TASK_ACKS_LATE = True

# # Monitoring
# CELERY_SEND_TASK_EVENTS = True
# CELERY_SEND_EVENTS = True

# # Security (if using SSL)
# CELERY_BROKER_USE_SSL = os.environ.get('CELERY_BROKER_USE_SSL', 'False').lower() == 'true'
# CELERY_REDIS_BACKEND_USE_SSL = os.environ.get('CELERY_REDIS_BACKEND_USE_SSL', 'False').lower() == 'true'

# # Development settings
# if DEBUG:
#     # In development, you might want to see all task outputs
#     CELERY_TASK_EAGER_PROPAGATES = True
#     CELERY_WORKER_LOG_LEVEL = 'DEBUG'
# else:
#     # Production settings
#     CELERY_WORKER_LOG_LEVEL = 'INFO'
    
# # Custom settings for scraping
# SCRAPING_SETTINGS = {
#     'RATE_LIMIT_MIN_DELAY': int(os.environ.get('SCRAPING_RATE_LIMIT_MIN', 1)),
#     'RATE_LIMIT_MAX_DELAY': int(os.environ.get('SCRAPING_RATE_LIMIT_MAX', 3)),
#     'MAX_RETRIES': int(os.environ.get('SCRAPING_MAX_RETRIES', 3)),
#     'RETRY_DELAY': int(os.environ.get('SCRAPING_RETRY_DELAY', 300)),
# }

# # Telegram message retention (days)
# TELEGRAM_MESSAGE_RETENTION_DAYS = 30

# # Maximum messages per API call
# TELEGRAM_MAX_MESSAGES_PER_CALL = 200

# # Message retry settings
# TELEGRAM_MAX_RETRIES = 3
# TELEGRAM_RETRY_DELAY = 300  # seconds

# # Telegram Bot
# TELEGRAM_BOT_TOKEN = '8562045503:AAEcuSIpQNGYlet0Kc-2z8wVSkCENMBTsfg'
# TELEGRAM_BOT_USERNAME = 'telegram_bot'
# TELEGRAM_BOT_PASSWORD = 'Bot@12345'

# # Frontend URL for email links
# FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# TELEGRAM_BYPASS_SUBSCRIPTION = True  # Only for dev!


