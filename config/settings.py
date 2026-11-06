import os
import tempfile
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
IS_VERCEL = os.environ.get('VERCEL') == '1'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if IS_VERCEL and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith('REPLACE_')):
    raise ImproperlyConfigured('Vercel 必须设置至少 50 字符的随机 DJANGO_SECRET_KEY。')
SECRET_KEY = SECRET_KEY or 'classroom-local-demo-only-change-before-public-deployment'
DEBUG = not IS_VERCEL and os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [v.strip() for v in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if v.strip()]
for key in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL'):
    host = os.environ.get(key, '').strip()
    if host and host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)
CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if v.strip()]
if IS_VERCEL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
WSGI_APPLICATION = 'config.wsgi.application'
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'market']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
database_url = os.environ.get('DATABASE_URL', '')
if database_url:
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(database_url, conn_max_age=0)}
    if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('云端 DATABASE_URL 必须指向 PostgreSQL。')
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
    DATABASES['default'].setdefault('OPTIONS', {})['connect_timeout'] = 10
    if IS_VERCEL:
        DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = 'require'
elif IS_VERCEL:
    raise ImproperlyConfigured('Vercel 需要 DATABASE_URL；不可使用本地 SQLite 或临时目录代替持久化数据库。')
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Hong_Kong'
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

# Vercel collects static files to its CDN; uploads use PostgreSQL for this small classroom demo.
STATIC_ROOT = BASE_DIR / 'staticfiles'
USE_DATABASE_MEDIA = IS_VERCEL or os.environ.get('CAMPUS_DATABASE_MEDIA') == '1'
STORAGES = {
    'default': {'BACKEND': 'market.storage.DatabaseImageStorage' if USE_DATABASE_MEDIA else 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
# Vercel has a request body limit, so allow images up to 3 MB, leaving room for form fields.
PRODUCT_IMAGE_MAX_BYTES = 3 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = PRODUCT_IMAGE_MAX_BYTES + 65536
FILE_UPLOAD_TEMP_DIR = tempfile.gettempdir() if IS_VERCEL else None
