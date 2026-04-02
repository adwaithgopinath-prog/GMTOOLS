import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-12345")
    SQLALCHEMY_DATABASE_URI = "sqlite:///inventory.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
