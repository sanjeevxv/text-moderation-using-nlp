from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Secret key
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-8@db)_kmhew8%i1!4lhlxf2a)6f)zadmj6w#=6y#$aex6bd64^'
)

# Debug
# Set DEBUG to True if the DJANGO_DEBUG environment variable is 'true' (case-insensitive)
# The default is False for safety in production.
DEBUG = True

# Hosts
raw_allowed_hosts = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    '127.0.0.1,localhost,safe-net.onrender.com'
)
ALLOWED_HOSTS = [h.strip() for h in raw_allowed_hosts.split(',') if h.strip()]

# CSRF Trusted Origins (must include https:// for Render)
raw_csrf_origins = os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000,https://safe-net.onrender.com'
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in raw_csrf_origins.split(',') if o.strip()]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'moderation',
    'dashboard',
    'django_extensions'
]

MIDDLEWARE = [
    # Gzip WhiteNoise middleware should be placed right after SecurityMiddleware in production.
    # If using Whitenoise, uncomment this line:
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
    
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'safenet.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'safenet.wsgi.application'

# Database (SQLite for local, Postgres for Render)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),  # Ensure string path for SQLite
        'OPTIONS': {
            'timeout': 60,  # Increased timeout to 60 seconds
            'check_same_thread': False,  # Allow multiple threads
            'isolation_level': 'IMMEDIATE',  # Better concurrency control
            # SQLite specific optimizations
            'init_command': '''
                PRAGMA journal_mode=WAL;
                PRAGMA cache_size=-2000;
                PRAGMA busy_timeout=30000;
                PRAGMA synchronous=NORMAL;
                PRAGMA temp_store=MEMORY;
            ''',
        }
    }
}

# If DATABASE_URL is set (for production), use that instead
if 'DATABASE_URL' in os.environ and os.environ['DATABASE_URL'].strip():
    DATABASES['default'] = dj_database_url.parse(
        os.environ['DATABASE_URL'],
        conn_max_age=600,
        ssl_require=True,
    )
    # For PostgreSQL, we don't need SQLite-specific optimizations
    if DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
        DATABASES['default']['OPTIONS'] = {}
        if 'init_commands' in DATABASES['default']:
            del DATABASES['default']['init_commands']

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.file'  # Use file-based sessions
SESSION_FILE_PATH = os.path.join(BASE_DIR, 'sessions')  # Directory to store session files
os.makedirs(SESSION_FILE_PATH, exist_ok=True)  # Ensure the directory exists

# Static files
STATIC_URL = '/static/'
# This path is where 'collectstatic' will place all static files in production.
STATIC_ROOT = BASE_DIR / 'staticfiles' 
# Removed os.environ.get('STATIC_ROOT', ...) for simplicity and consistency.

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Gemini API key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Auth redirects
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/users/login/'

# ======= 🔒 PRODUCTION/SECURITY SETTINGS for Render HTTPS =======
# These settings will ONLY be active when DEBUG=False (i.e., on Render)

# Trust the Render proxy headers for SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies will only be sent over HTTPS
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Force redirect to HTTPS only when DEBUG is False (i.e., in production)
SECURE_SSL_REDIRECT = not DEBUG 

# Add HSTS headers for extra security
# HSTS is a browser-level policy telling it to only connect via HTTPS
# Set a max age to 1 year (31536000 seconds)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True


# Optional: prevent mixed content issues on HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True