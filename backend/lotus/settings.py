"""
Django settings for lotus project.

Generated by 'django-admin startproject' using Django 4.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import datetime
import logging
import os
import re
import ssl
from datetime import timedelta, timezone
from json import loads
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
import django_heroku
import jwt
import kafka_helper
import posthog
import sentry_sdk
from decouple import config
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from sentry_sdk.integrations.django import DjangoIntegration
from svix.api import EventTypeIn, Svix, SvixAsync, SvixOptions

logger = logging.getLogger("django.server")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
try:
    path = Path(__file__).resolve().parent.parent.parent / "env/.env.test"
    load_dotenv(dotenv_path=path)
except:
    pass

VITE_API_URL = config("VITE_API_URL", default="http://localhost:8000")
VITE_STRIPE_CLIENT = config("VITE_STRIPE_CLIENT", default="")
EVENT_CACHE_FLUSH_SECONDS = config("EVENT_CACHE_FLUSH_SECONDS", default=180, cast=int)
EVENT_CACHE_FLUSH_COUNT = config("EVENT_CACHE_FLUSH_COUNT", default=1000, cast=int)
DOCKERIZED = config("DOCKERIZED", default=False, cast=bool)
ON_HEROKU = config("ON_HEROKU", default=False, cast=bool)
DEBUG = config("DEBUG", default=False, cast=bool)
PROFILER_ENABLED = config("PROFILER_ENABLED", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY", default="")
if SECRET_KEY == "":
    SECRET_KEY = os.urandom(32)
    logger.info("SECRET_KEY not set. Defaulting to a random one.")
POSTGRES_DB = config("POSTGRES_DB", default="lotus")
POSTGRES_USER = config("POSTGRES_USER", default="lotus")
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", default="lotus")
SENTRY_DSN = config("SENTRY_DSN", default="")
SELF_HOSTED = config("SELF_HOSTED", default=False, cast=bool)
PRODUCT_ANALYTICS_OPT_IN = config("PRODUCT_ANALYTICS_OPT_IN", default=True, cast=bool)
PRODUCT_ANALYTICS_OPT_IN = True if not SELF_HOSTED else PRODUCT_ANALYTICS_OPT_IN
# Stripe required
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="whsec_")
# Webhooks for Svix
SVIX_API_KEY = config("SVIX_API_KEY", default="")
SVIX_JWT_SECRET = config("SVIX_JWT_SECRET", default="")
# Optional Observalility Services
CRONITOR_API_KEY = config("CRONITOR_API_KEY", default="")

if SENTRY_DSN != "":
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
        ],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
    )


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

API_KEY_CUSTOM_HEADER = "X-API-KEY"

posthog.project_api_key = config(
    "POSTHOG_API_KEY", default="phc_6HB6j1Hp68ESe2FpvodVwF48oisXYpot5Ymc06SbY9M"
)
posthog.host = "https://app.posthog.com"

if not PRODUCT_ANALYTICS_OPT_IN or DEBUG:
    posthog.disabled = True
POSTHOG_PERSON = "self_hosted_" + str(hash(SECRET_KEY)) if SELF_HOSTED else None

if DEBUG or SELF_HOSTED:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = [
        "*uselotus.io",
    ]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "djmoney",
    "django_extensions",
    "django_celery_beat",
    "rest_framework_api_key",
    "drf_spectacular",
    "simple_history",
    "knox",
    "anymail",
    "api",
    "metering_billing",
    "actstream",
    "drf_standardized_errors",
    "storages",
]

SITE_ID = 1


ANYMAIL = {
    "MAILGUN_API_KEY": os.environ.get("MAILGUN_API_KEY"),
    "MAILGUN_DOMAIN": os.environ.get("MAILGUN_DOMAIN"),
    "MAILGUN_PUBLIC_KEY": os.environ.get("MAILGUN_PUBLIC_KEY"),
    "MAILGUN_SMTP_LOGIN": os.environ.get("MAILGUN_SMTP_LOGIN"),
    "MAILGUN_SMTP_PASSWORD": os.environ.get("MAILGUN_SMTP_PASSWORD"),
    "MAILGUN_SMTP_PORT": os.environ.get("MAILGUN_SMTP_PORT"),
    "MAILGUN_SMTP_SERVER": os.environ.get("MAILGUN_SMTP_SERVER"),
}

if ON_HEROKU:
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    APP_URL = "https://app.uselotus.io"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    APP_URL = "http://localhost:8000"


EMAIL_DOMAIN = os.environ.get("MAILGUN_DOMAIN")
EMAIL_USERNAME = "noreply"
DEFAULT_FROM_EMAIL = f"{EMAIL_USERNAME}@{EMAIL_DOMAIN}"
# ditto (default from-email for Django errors)
SERVER_EMAIL = "you@uselotus.io"

if PROFILER_ENABLED:
    INSTALLED_APPS.append("silk")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "metering_billing.middleware.OrganizationInsertMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

if PROFILER_ENABLED:
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
    SILKY_PYTHON_PROFILER = True


ROOT_URLCONF = "lotus.urls"

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

WSGI_APPLICATION = "lotus.wsgi.application"

AUTH_USER_MODEL = "metering_billing.User"
AUTHENTICATION_BACKENDS = ["metering_billing.model_backend.EmailOrUsernameModelBackend"]
SOCIAL_AUTH_JSONFIELD_ENABLED = True
# SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# SESSION_COOKIE_AGE = 2 * 60 * 60  # set just 10 seconds to test
# SESSION_SAVE_EVERY_REQUEST = True

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.parse(
            os.environ["DATABASE_URL"],
            engine="django.db.backends.postgresql",
            conn_max_age=600,
        )
    }
    django_heroku.settings(locals(), databases=False)
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": POSTGRES_DB,
            "USER": POSTGRES_USER,
            "PASSWORD": POSTGRES_PASSWORD,
            "HOST": "db" if DOCKERIZED else "localhost",
            "PORT": 5432,
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


def value_deserializer(value):
    try:
        return loads(value.decode("utf-8"))
    except Exception as e:
        logger.error("Value deserialization error:", e)
        return None


def key_deserializer(key):
    try:
        return key.decode("utf-8")
    except Exception as e:
        logger.error("Key deserialization error:", e)
        return None


# Kafka/Redpanda Settings
KAFKA_PREFIX = config("KAFKA_PREFIX", default="")
KAFKA_EVENTS_TOPIC = KAFKA_PREFIX + config("EVENTS_TOPIC", default="test-topic")
if type(KAFKA_EVENTS_TOPIC) is bytes:
    KAFKA_EVENTS_TOPIC = KAFKA_EVENTS_TOPIC.decode("utf-8")
KAFKA_NUM_PARTITIONS = config("NUM_PARTITIONS", default=10, cast=int)
KAFKA_REPLICATION_FACTOR = config("REPLICATION_FACTOR", default=1, cast=int)
KAFKA_HOST = config("KAFKA_URL", default="127.0.0.1:9092")
if KAFKA_HOST:
    if "," not in KAFKA_HOST:
        KAFKA_HOST = KAFKA_HOST
    else:
        KAFKA_HOST = [
            "{}:{}".format(parsedUrl.hostname, parsedUrl.port)
            for parsedUrl in [urlparse(url) for url in KAFKA_HOST.split(",")]
        ]
    producer_config = {
        "bootstrap_servers": KAFKA_HOST,
        "api_version": (2, 5, 0),
    }
    consumer_config = {
        "bootstrap_servers": KAFKA_HOST,
        "auto_offset_reset": "earliest",
        "value_deserializer": value_deserializer,
        "key_deserializer": key_deserializer,
        "api_version": (2, 5, 0),
    }
    admin_client_config = {
        "bootstrap_servers": KAFKA_HOST,
        "client_id": "events-client",
    }

    KAFKA_CERTIFICATE = config("KAFKA_CLIENT_CERT", default=None)
    KAFKA_KEY = config("KAFKA_CLIENT_CERT_KEY", default=None)
    KAFKA_CA = config("KAFKA_TRUSTED_CERT", default=None)
    if KAFKA_CERTIFICATE and KAFKA_KEY and KAFKA_CA:
        ssl_context = kafka_helper.get_kafka_ssl_context()
        for cfg in [producer_config, consumer_config, admin_client_config]:
            cfg["security_protocol"] = "SSL"
            cfg["ssl_context"] = ssl_context

    PRODUCER_CONFIG = producer_config
    CONSUMER = KafkaConsumer(KAFKA_EVENTS_TOPIC, **consumer_config)
    ADMIN_CLIENT = KafkaAdminClient(**admin_client_config)

    existing_topics = ADMIN_CLIENT.list_topics()
    if KAFKA_EVENTS_TOPIC not in existing_topics and SELF_HOSTED:
        try:
            ADMIN_CLIENT.create_topics(
                new_topics=[
                    NewTopic(
                        name=KAFKA_EVENTS_TOPIC,
                        num_partitions=KAFKA_NUM_PARTITIONS,
                        replication_factor=KAFKA_REPLICATION_FACTOR,
                    )
                ]
            )
        except TopicAlreadyExistsError:
            pass
else:
    PRODUCER_CONFIG = None
    CONSUMER = None

# redis settings
if os.environ.get("REDIS_URL"):
    REDIS_URL = (
        os.environ.get("REDIS_TLS_URL")
        if os.environ.get("REDIS_TLS_URL")
        else os.environ.get("REDIS_URL")
    )
elif DOCKERIZED:
    REDIS_URL = f"redis://redis:6379"
else:
    REDIS_URL = f"redis://localhost:6379"

# Celery Settings
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/0"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/New_York"

if ON_HEROKU:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_URL}/0",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "REDIS_CLIENT_KWARGS": {"ssl_cert_reqs": ssl.CERT_NONE},
                "CONNECTION_POOL_KWARGS": {"ssl_cert_reqs": None},
            },
        }
    }
elif DOCKERIZED:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{REDIS_URL}/3",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(asctime)s [%(process)d] [%(levelname)s] "
                + "pathname=%(pathname)s lineno=%(lineno)s "
                + "funcname=%(funcName)s %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
        }
    },
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

INTERNAL_IPS = ["127.0.0.1"]
if DOCKERIZED:
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]
    try:
        _, _, ips = socket.gethostbyname_ex("frontend")
        INTERNAL_IPS.extend(ips)
    except socket.gaierror:
        logger.error(
            "tried to get frontend container ip but failed, current internal ips:",
            INTERNAL_IPS,
        )
        pass

VITE_APP_DIR = BASE_DIR / "src"


### AWS S3 ###
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_S3_INVOICE_BUCKET = os.environ["AWS_S3_INVOICE_BUCKET"]


STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "static/"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
STATICFILES_DIRS = [BASE_DIR / "static", VITE_APP_DIR / "dist"]


MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "metering_billing.permissions.ValidOrganization",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "knox.auth.TokenAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler",
    "COERCE_DECIMAL_TO_STRING": False,
}

DRF_STANDARDIZED_ERRORS = {
    # class responsible for handling the exceptions. Can be subclassed to change
    # which exceptions are handled by default, to update which exceptions are
    # reported to error monitoring tools (like Sentry), ...
    "EXCEPTION_HANDLER_CLASS": "metering_billing.exceptions.handler.CustomHandler",
    # class responsible for generating error response output. Can be subclassed
    # to change the format of the error response.
    "EXCEPTION_FORMATTER_CLASS": "metering_billing.exceptions.handler.RFC7807Formatter",
    # enable the standardized errors when DEBUG=True for unhandled exceptions.
    # By default, this is set to False so you're able to view the traceback in
    # the terminal and get more information about the exception.
    "ENABLE_IN_DEBUG_FOR_UNHANDLED_EXCEPTIONS": False,
    # The below settings are for OpenAPI 3 schema generation
    # ONLY the responses that correspond to these status codes will appear
    # in the API schema.
    "ALLOWED_ERROR_STATUS_CODES": [
        "400",
        "401",
        "403",
        "404",
        "405",
        "406",
        "415",
        "429",
        "500",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Lotus API",
    "DESCRIPTION": (
        "Lotus is an open-core pricing and billing engine. We enable API companies to"
        " automate and optimize their custom usage-based pricing for any metric."
    ),
    "VERSION": "0.0.1",
    "SERVE_INCLUDE_SCHEMA": False,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "OrganizationApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-KEY",
            },
        }
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [
        {
            "OrganizationApiKeyAuth": [],
            "TokenAuth": [],
        }
    ],
    "PREPROCESSING_HOOKS": [
        "metering_billing.openapi_hooks.remove_invalid_subscription_methods"
    ],
    "POSTPROCESSING_HOOKS": [
        "metering_billing.openapi_hooks.remove_required_parent_plan_and_target_customer",
        "metering_billing.openapi_hooks.remove_required_external_payment_obj_type",
        "metering_billing.openapi_hooks.add_external_payment_obj_type_to_required",
        "metering_billing.openapi_hooks.add_plan_id_parent_plan_target_customer_to_required",
        "metering_billing.openapi_hooks.remove_required_address_from_lw_cust_invoice",
    ],
    "ENUM_NAME_OVERRIDES": {
        "numeric_filter_operators": "metering_billing.utils.enums.NUMERIC_FILTER_OPERATORS.choices",
        "categorical_filter_operators": "metering_billing.utils.enums.CATEGORICAL_FILTER_OPERATORS.choices",
        "BacktestStatusEnum": "metering_billing.utils.enums.BACKTEST_STATUS.choices",
        "BacktestKPIEnum": "metering_billing.utils.enums.BACKTEST_KPI.choices",
        "PaymentProvidersEnum": "metering_billing.utils.enums.PAYMENT_PROVIDERS.choices",
        "FlatFeeBillingTypeEnum": "metering_billing.utils.enums.FLAT_FEE_BILLING_TYPE.choices",
        "MetricAggregationEnum": "metering_billing.utils.enums.METRIC_AGGREGATION.choices",
        "MetricGranularityEnum": "metering_billing.utils.enums.METRIC_GRANULARITY.choices",
        "PlanVersionStatusEnum": "metering_billing.utils.enums.PLAN_VERSION_STATUS.choices",
        "PlanStatusEnum": "metering_billing.utils.enums.PLAN_STATUS.choices",
        "BacktestStatusEnum": "metering_billing.utils.enums.BACKTEST_STATUS.choices",
        "ProductStatusEnum": "metering_billing.utils.enums.PRODUCT_STATUS.choices",
        "InvoiceStatusEnum": "metering_billing.utils.enums.INVOICE_STATUS.choices",
        "FailureStatusEnum": ["eror"],
        "SuccessStatusEnum": ["success"],
        "TrackEventSuccessEnum": ["all", "some"],
        "TrackEventFailureEnum": ["none"],
        "OrganizationUserStatus": "metering_billing.utils.enums.ORGANIZATION_STATUS.choices",
        "ValidationErrorEnum": "drf_standardized_errors.openapi_serializers.ValidationErrorEnum.values",
        "ClientErrorEnum": "drf_standardized_errors.openapi_serializers.ClientErrorEnum.values",
        "ServerErrorEnum": "drf_standardized_errors.openapi_serializers.ServerErrorEnum.values",
        "ErrorCode401Enum": "drf_standardized_errors.openapi_serializers.ErrorCode401Enum.values",
        "ErrorCode403Enum": "drf_standardized_errors.openapi_serializers.ErrorCode403Enum.values",
        "ErrorCode404Enum": "drf_standardized_errors.openapi_serializers.ErrorCode404Enum.values",
        "ErrorCode405Enum": "drf_standardized_errors.openapi_serializers.ErrorCode405Enum.values",
        "ErrorCode406Enum": "drf_standardized_errors.openapi_serializers.ErrorCode406Enum.values",
        "ErrorCode415Enum": "drf_standardized_errors.openapi_serializers.ErrorCode415Enum.values",
        "ErrorCode429Enum": "drf_standardized_errors.openapi_serializers.ErrorCode429Enum.values",
        "ErrorCode500Enum": "drf_standardized_errors.openapi_serializers.ErrorCode500Enum.values",
    },
}

REST_KNOX = {
    "TOKEN_TTL": timedelta(hours=2),
    "AUTO_REFRESH": True,
}

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# if DEBUG:
#     CORS_ALLOW_ALL_ORIGINS = True
# else:
#     CORS_ALLOWED_ORIGIN_REGEXES = [
#         r"^https://\w+\.uselotus\.io$",
#     ]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-api-key",
    "X-API-KEY",
]

CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = ["https://*.uselotus.io"]


# Vite generates files with 8 hash digits
# http://whitenoise.evans.io/en/stable/django.html#WHITENOISE_IMMUTABLE_FILE_TEST


def immutable_file_test(path, url):
    # Match filename with 12 hex digits before the extension
    # e.g. app.db8f2edc0c8a.js
    return re.match(r"^.+\.[0-9a-f]{8,12}\..+$", url)


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test

LOTUS_HOST = config("LOTUS_HOST", default=None)
LOTUS_API_KEY = config("LOTUS_API_KEY", default=None)
META = LOTUS_API_KEY and LOTUS_HOST
# Heroku
django_heroku.settings(locals(), logging=False)

# create svix events
if SVIX_API_KEY != "":
    svix = Svix(SVIX_API_KEY)
elif SVIX_API_KEY == "" and SVIX_JWT_SECRET != "":
    try:
        dt = datetime.datetime.now(timezone.utc)
        utc_time = dt.replace(tzinfo=timezone.utc)
        utc_timestamp = utc_time.timestamp()
        payload = {
            "iat": utc_timestamp,
            "exp": 2980500639,
            "nbf": utc_timestamp,
            "iss": "svix-server",
            "sub": "org_23rb8YdGqMT0qIzpgGwdXfHirMu",
        }
        encoded = jwt.encode(payload, SVIX_JWT_SECRET, algorithm="HS256")
        SVIX_API_KEY = encoded
        hostname, _, ips = socket.gethostbyname_ex("svix-server")
        svix = Svix(SVIX_API_KEY, SvixOptions(server_url=f"http://{ips[0]}:8071"))
    except Exception as e:
        svix = None
else:
    svix = None
SVIX_CONNECTOR = svix

if SVIX_CONNECTOR is not None:
    try:
        svix = SVIX_CONNECTOR
        list_response_event_type_out = [x.name for x in svix.event_type.list().data]
        if "invoice.created" not in list_response_event_type_out:
            event_type_out = svix.event_type.create(
                EventTypeIn(
                    description="Invoice is created",
                    archived=False,
                    name="invoice.created",
                )
            )
        if "invoice.paid" not in list_response_event_type_out:
            event_type_out = svix.event_type.create(
                EventTypeIn(
                    description="Invoice is marked as paid",
                    archived=False,
                    name="invoice.paid",
                )
            )
    except:
        SVIX_CONNECTOR = None
