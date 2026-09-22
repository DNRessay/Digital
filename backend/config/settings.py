import os
from decimal import Decimal
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
    "corsheaders",
    "builder",
]

MIDDLEWARE = [
    "config.request_log_middleware.RequestLogMiddleware",
    "config.custom_domain_middleware.CustomDomainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "config.trailing_slash_middleware.RestoreStrippedTrailingSlashMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# The frontend/admin and frontend/web-portal React apps are deployed
# separately on Cloudflare Pages — a different origin from this backend —
# and need to call the JSON API with the session cookie attached.
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()]
CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = FRONTEND_ORIGINS

if not DEBUG:
    # SameSite=None is what lets the browser attach these cookies to a
    # cross-origin fetch(credentials:'include') call from a Pages domain;
    # it requires Secure, which is why this is production-only (local dev
    # runs on plain http and would silently stop setting cookies at all).
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

_using_external_db = bool(os.environ.get("DATABASE_URL"))

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        conn_max_age=600,
        ssl_require=_using_external_db and os.environ.get("DJANGO_DB_SSL_REQUIRE", "true").lower() == "true",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Template assets (and any other uploaded media) must survive Lambda's
# ephemeral filesystem, so use S3 whenever a bucket is configured — falls
# back to local disk for local development only.
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
if AWS_STORAGE_BUCKET_NAME:
    AWS_S3_REGION_NAME = os.environ.get("AWS_REGION", "eu-west-1")
    # Every asset path is namespaced by Template.slug, which is DB-unique,
    # so two templates can never collide — safe to skip the extra
    # exists()-check HEAD request storages does per file when this is False,
    # which matters a lot under the 29s API Gateway timeout budget.
    AWS_S3_FILE_OVERWRITE = True
    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = None
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}

TEMPLIFY_FUNCTION_URL = os.environ.get(
    "TEMPLIFY_FUNCTION_URL", "https://dmt46thjvn6fyzwxfmpfwae7li0ccmyc.lambda-url.eu-west-1.on.aws/"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
CONTACT_RECIPIENT_EMAIL = os.environ.get("CONTACT_RECIPIENT_EMAIL", "")

# PayFast (builder/services/payfast.py) — removes a Site's "Powered by
# Vicinic" credit once a package subscription is active. Defaults are
# PayFast's own published sandbox test-merchant credentials (safe, public,
# meant for exactly this) so this works out of the box in dev; production
# must override all three with a real merchant account and set
# PAYFAST_SANDBOX=false.
PAYFAST_MERCHANT_ID = os.environ.get("PAYFAST_MERCHANT_ID", "10000100")
PAYFAST_MERCHANT_KEY = os.environ.get("PAYFAST_MERCHANT_KEY", "46f0cd694581a")
PAYFAST_PASSPHRASE = os.environ.get("PAYFAST_PASSPHRASE", "")
PAYFAST_SANDBOX = os.environ.get("PAYFAST_SANDBOX", "true").lower() == "true"

# Cloudflare (builder/services/cloudflare.py) — connecting a customer's own
# domain and Email Routing on it for the "Deploy" tab. CLOUDFLARE_API_TOKEN
# needs Zone:Edit, Zone:DNS:Edit, Zone Email Routing Rules:Edit and
# Account:Zone:Edit; CLOUDFLARE_ACCOUNT_ID is the account every customer
# domain becomes a zone under (see that module's docstring for why).
# PLATFORM_ORIGIN_HOST is this backend's own Lambda Function URL host (no
# scheme) — the DNS target a connected domain's zone gets pointed at; it
# can't be derived automatically (self-referencing a Function's own
# generated URL from within its own environment variables is a circular
# CloudFormation dependency), so it's a parameter, same as
# TEMPLIFY_FUNCTION_URL above, and needs updating if this stack is ever
# torn down and redeployed as a new function (a plain redeploy keeps the
# same URL).
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
PLATFORM_ORIGIN_HOST = os.environ.get(
    "PLATFORM_ORIGIN_HOST", "uoby5fryqkhbasb7wicrtg5oiq0pgwth.lambda-url.eu-west-1.on.aws"
)

# In-app domain purchase (builder/services/cloudflare.py check_domain/
# register_domain, builder/customer_api.py domain-purchase endpoints).
# Cloudflare Registrar bills Vicinic's own Cloudflare account directly, at
# cost, usually in USD — DOMAIN_EXCHANGE_RATE_ZAR converts that to what the
# customer is actually charged via PayFast (which only settles in ZAR), and
# DOMAIN_MARKUP_ZAR is added on top. Both are plain settings rather than a
# live FX API call: registrations are non-refundable, so a stale-but-known
# rate that's manually nudged occasionally is safer than a live rate that
# could put a purchase underwater between quote and payment.
DOMAIN_EXCHANGE_RATE_ZAR = Decimal(os.environ.get("DOMAIN_EXCHANGE_RATE_ZAR", "18.50"))
DOMAIN_MARKUP_ZAR = Decimal(os.environ.get("DOMAIN_MARKUP_ZAR", "30.00"))

# HostAfrica Domains Reseller (builder/services/hostafrica.py) — the .co.za
# counterpart to Cloudflare Registrar above, since Cloudflare doesn't sell
# .za domains. HOSTAFRICA_API_EMAIL is the reseller account's login email
# (used as the HMAC key, not sent as a password); HOSTAFRICA_API_KEY is the
# API key from Client Area → Domains → Reseller Area → Integrations. Prices
# here are already ZAR, so only DOMAIN_MARKUP_ZAR applies — no exchange
# rate, unlike the Cloudflare (USD) path.
HOSTAFRICA_API_EMAIL = os.environ.get("HOSTAFRICA_API_EMAIL", "")
HOSTAFRICA_API_KEY = os.environ.get("HOSTAFRICA_API_KEY", "")

# WhatsApp Cloud API (builder/services/whatsapp.py, builder/whatsapp_views.py,
# customer_api.api_customer_site_whatsapp) — lets a customer connect their
# own WhatsApp number to their Site via Meta's Embedded Signup, all through
# Vicinic's single "BodCat" Meta app. WHATSAPP_ACCESS_TOKEN is that app's
# System User token (needs whatsapp_business_management +
# whatsapp_business_messaging permission, which requires Meta's Tech
# Provider status — see the app's own setup flow for where that's applied
# for). WHATSAPP_APP_ID/WHATSAPP_CONFIG_ID are what the Deploy tab's
# Embedded Signup button needs client-side (App Dashboard → WhatsApp →
# Embedded Signup → create a configuration to get WHATSAPP_CONFIG_ID).
# WHATSAPP_VERIFY_TOKEN must match exactly what's entered in the App
# Dashboard's Webhooks "Verify token" field (any string you choose).
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_APP_ID = os.environ.get("WHATSAPP_APP_ID", "")
WHATSAPP_CONFIG_ID = os.environ.get("WHATSAPP_CONFIG_ID", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

# AI chat widget (builder/services/ai_assistant.py) — a free-tier Hugging
# Face model answers simple visitor questions on a Site's rendered pages,
# using Site.ai_assistant_description as context. HUGGINGFACE_MODEL is a
# setting rather than hardcoded because Hugging Face's free-tier hosted
# models rotate over time; if the default stops responding, point this at
# whatever small instruct model is currently free on
# https://huggingface.co/models?inference=warm&pipeline_tag=text-generation
HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")
HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "HuggingFaceH4/zephyr-7b-beta")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
