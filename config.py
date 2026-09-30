import os
from datetime import timedelta


def _database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///inventory.db").strip()
    # Render and some other providers still expose the legacy postgres:// scheme.
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV in {"production", "prod"}
_secret_key = os.environ.get("FLASK_SECRET_KEY")
if IS_PRODUCTION and not _secret_key:
    raise RuntimeError("FLASK_SECRET_KEY must be set when APP_ENV=production.")
_database_uri = _database_url()
if IS_PRODUCTION and not _database_uri.startswith("postgresql+psycopg://"):
    raise RuntimeError("Set DATABASE_URL to the production PostgreSQL connection URL.")


class Config:
    APP_ENV = APP_ENV
    IS_PRODUCTION = IS_PRODUCTION
    SECRET_KEY = _secret_key or "dev-secret-key-12345"
    SQLALCHEMY_DATABASE_URI = _database_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
