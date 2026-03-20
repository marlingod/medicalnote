import os
import ssl

from .base import *  # noqa: F401,F403

DEBUG = False

# Security settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

# Redis TLS enforcement — HIPAA requires encryption in transit (§164.312(e)(1))
_REDIS_TLS_URL = os.environ.get("REDIS_TLS_URL", "")
if _REDIS_TLS_URL:
    CELERY_BROKER_URL = _REDIS_TLS_URL
    CELERY_RESULT_BACKEND = _REDIS_TLS_URL

    _SSL_CONF = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
    CELERY_BROKER_USE_SSL = _SSL_CONF
    CELERY_REDIS_BACKEND_USE_SSL = _SSL_CONF

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [_REDIS_TLS_URL],
            },
        },
    }
