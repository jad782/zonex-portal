"""إعدادات مشروع ZoneX Portal (موقع الاشتراكات)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل ملف .env تلقائياً إذا كان موجوداً (على السيرفر) — اختياري
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except Exception:
    pass

# ─────────────────────────────────────────────────────────────
#  الإعدادات الحسّاسة تُقرأ من متغيّرات البيئة (آمنة للإنتاج)
#  محلياً تشتغل بالقيم الافتراضية. على السيرفر تحدّد المتغيّرات.
# ─────────────────────────────────────────────────────────────

# مفتاح Django السري — على السيرفر ضع متغيّر DJANGO_SECRET_KEY
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'zx$pK7-9fLm3Qr2Tn8wB5xH4dJ0cG6sZaE1nY-vU2hP4kR8tW6'
)

# DEBUG=False تلقائياً على السيرفر إذا ضبطت DJANGO_DEBUG=False
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes', 'on')

# يسمح دائماً بالمحلي، ويُضاف الدومين من متغيّر DJANGO_ALLOWED_HOSTS
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
_extra_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
if _extra_hosts:
    ALLOWED_HOSTS += [h.strip() for h in _extra_hosts.split(',') if h.strip()]

# ⚠️ مهم جداً: نفس القيمة الموجودة في التطبيق المحلي (cafe/models.py: LICENSE_SECRET)
# حتى يقبل التطبيق المحلي كود التفعيل المُولّد من هنا.
LICENSE_SECRET = os.environ.get(
    'ZONEX_LICENSE_SECRET',
    'ZX2026_pK9fL3mQ7rT2vN8wB5xH4dJ0cG6sZ_aE1nY_LICENCE'
)

# رابط تحميل برنامج ZONE X (ملف التثبيت) — ضعه في .env بعد رفع الـ exe على Google Drive
DOWNLOAD_URL = os.environ.get('ZONEX_DOWNLOAD_URL', '')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'subscriptions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # يخدم ملفات static في الإنتاج
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# روابط موثوقة لـ CSRF (الدومين) — من متغيّر DJANGO_CSRF_ORIGINS مفصولة بفواصل
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_ORIGINS', '').split(',') if o.strip()
]

ROOT_URLCONF = 'portal_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'portal_core.wsgi.application'

# ─── قاعدة البيانات ───
# محلياً: SQLite تلقائياً.
# على السيرفر: حدّد DB_NAME + DB_USER + DB_PASSWORD ... ليتحوّل لـ PostgreSQL.
if os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER', ''),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'portal_db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Damascus'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── إعدادات الأمان للإنتاج (تُفعّل تلقائياً فقط لما DEBUG=False) ───
if not DEBUG:
    # whitenoise: ضغط وتخزين ملفات static
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SSL_REDIRECT', 'True').lower() in ('1', 'true', 'yes', 'on')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 2592000  # 30 يوم
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
