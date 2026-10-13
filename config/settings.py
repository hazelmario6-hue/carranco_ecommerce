import os
from pathlib import Path
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
def flag(key,default=False):
    return os.getenv(key,str(default)).lower() in {"true","1","yes"}
def names(key,default=""):
    return [item.strip() for item in os.getenv(key,default).split(",") if item.strip()]
DEBUG=flag("DEBUG")
SECRET_KEY=os.getenv("SECRET_KEY","")
if len(SECRET_KEY)<32:
    raise ImproperlyConfigured("Genera SECRET_KEY en tu .env (al menos 32 caracteres).")
ALLOWED_HOSTS=names("ALLOWED_HOSTS","localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS=names("CSRF_TRUSTED_ORIGINS")
INSTALLED_APPS=["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles"]+[f"apps.{name}" for name in ["core","catalogo","carrito","cuentas","pedidos","pagos","dashboard"]]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware","apps.core.middleware.SensitivePagesMiddleware",]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","apps.carrito.context_processors.cart_context"]}}]
WSGI_APPLICATION="config.wsgi.application"
ASGI_APPLICATION="config.asgi.application"
test_database=os.getenv("TEST_DB_NAME","test_carranco_django")
if not test_database.startswith("test_") or test_database==os.getenv("DB_NAME","carranco_django"):
    raise ImproperlyConfigured("TEST_DB_NAME debe comenzar por test_ y ser distinto de DB_NAME.")
DATABASES={"default":{"ENGINE":"django.db.backends.mysql","NAME":os.getenv("DB_NAME","carranco_django"),"USER":os.getenv("DB_USER",""),"PASSWORD":os.getenv("DB_PASSWORD",""),"HOST":os.getenv("DB_HOST","127.0.0.1"),"PORT":os.getenv("DB_PORT","3306"),"OPTIONS":{"charset":"utf8mb4","init_command":"SET sql_mode='STRICT_TRANS_TABLES'","isolation_level":"read committed"},"CONN_MAX_AGE":60,"TEST":{"NAME":test_database}}}
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator","OPTIONS":{"min_length":12}},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE="es-mx"
TIME_ZONE="America/Mexico_City"
USE_I18N=True
USE_TZ=True
STATIC_URL="/static/"
STATICFILES_DIRS=[BASE_DIR/"static"]
STATIC_ROOT=BASE_DIR/"staticfiles"
MEDIA_URL="/media/"
MEDIA_ROOT=BASE_DIR/"media"
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="cuentas:login"
LOGIN_REDIRECT_URL="cuentas:perfil"
LOGOUT_REDIRECT_URL="core:index"
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE="Lax"
SESSION_COOKIE_AGE=int(os.getenv("SESSION_COOKIE_AGE","3600"))
SESSION_SAVE_EVERY_REQUEST=True
SESSION_EXPIRE_AT_BROWSER_CLOSE=True
CSRF_COOKIE_HTTPONLY=True
SESSION_COOKIE_SECURE=not DEBUG
CSRF_COOKIE_SECURE=not DEBUG
SECURE_SSL_REDIRECT=not DEBUG
SECURE_HSTS_SECONDS=0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=not DEBUG
SECURE_HSTS_PRELOAD=not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY="same-origin"
X_FRAME_OPTIONS="DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE=2*1024*1024
if flag("TRUST_PROXY_HTTPS"):
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
FILE_UPLOAD_MAX_MEMORY_SIZE=2*1024*1024
ACADEMIC_MODE=flag("ACADEMIC_MODE",True)
try:
    ACADEMIC_CHARGE_AMOUNT=Decimal(os.environ["ACADEMIC_CHARGE_AMOUNT"]) if os.getenv("ACADEMIC_CHARGE_AMOUNT") else None
    ACADEMIC_MAX_CHARGE=Decimal(os.getenv("ACADEMIC_MAX_CHARGE","100.00"))
except InvalidOperation:
    raise ImproperlyConfigured("Configura importes académicos numéricos en .env.")
if (ACADEMIC_CHARGE_AMOUNT is not None and (not ACADEMIC_CHARGE_AMOUNT.is_finite() or ACADEMIC_CHARGE_AMOUNT<=0 or ACADEMIC_CHARGE_AMOUNT!=ACADEMIC_CHARGE_AMOUNT.quantize(Decimal("0.01")))) or not ACADEMIC_MAX_CHARGE.is_finite() or ACADEMIC_MAX_CHARGE<=0:
    raise ImproperlyConfigured("Los importes académicos deben ser positivos y finitos.")
STOCK_LOW_THRESHOLD=int(os.getenv("STOCK_LOW_THRESHOLD","5"))
RESERVATION_MINUTES=int(os.getenv("RESERVATION_MINUTES","30"))
if not 1<=RESERVATION_MINUTES<=1440 or not 1<=STOCK_LOW_THRESHOLD<=10000:
    raise ImproperlyConfigured("Revisa la duración de reserva y el umbral de stock.")
APP_URL=os.getenv("APP_URL","http://localhost:8000").rstrip("/")
PAYMENTS_LIVE=flag("PAYMENTS_LIVE")
MP_ACCESS_TOKEN=os.getenv("MP_ACCESS_TOKEN","")
MP_WEBHOOK_SECRET=os.getenv("MP_WEBHOOK_SECRET","")
OPENPAY_MERCHANT_ID=os.getenv("OPENPAY_MERCHANT_ID","")
OPENPAY_PRIVATE_KEY=os.getenv("OPENPAY_PRIVATE_KEY","")
OPENPAY_PRODUCTION=flag("OPENPAY_PRODUCTION")
OPENPAY_WEBHOOK_USER=os.getenv("OPENPAY_WEBHOOK_USER","")
OPENPAY_WEBHOOK_PASSWORD=os.getenv("OPENPAY_WEBHOOK_PASSWORD","")
if (not DEBUG or PAYMENTS_LIVE) and not APP_URL.startswith("https://"):
    raise ImproperlyConfigured("La producción y los cobros reales requieren APP_URL HTTPS.")
if PAYMENTS_LIVE and not ACADEMIC_MODE:
    raise ImproperlyConfigured("Este proyecto habilita cobros únicamente en ACADEMIC_MODE.")

if PAYMENTS_LIVE and DEBUG:
    raise ImproperlyConfigured("Para cobros reales configura DEBUG=False y HTTPS.")
