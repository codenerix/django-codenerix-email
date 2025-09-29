SECRET_KEY = "a-key-for-testing"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "codenerix",
    "codenerix_email",
]

CLIENT_EMAIL_HOST = ""
CLIENT_EMAIL_PORT = 0
CLIENT_EMAIL_USERNAME = ""
CLIENT_EMAIL_PASSWORD = ""
CLIENT_EMAIL_USE_TLS = False
CLIENT_EMAIL_USE_SSL = False

LANGUAGES_DATABASES = ["EN"]

# A minimal database config is sometimes needed
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
