import os
from datetime import timedelta
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-campusconnect-change-in-production-2024")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///campusconnect.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024   # 20 MB hard limit
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}


# Enable WAL mode and busy timeout for SQLite to handle concurrent workers
# (Finding 9 fix)
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, conn_record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
