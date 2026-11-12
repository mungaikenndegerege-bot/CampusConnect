"""
seed.py — Run before gunicorn (or during run.py startup).
Creates DB tables and seeds the super admin if none exists.

Super admin credentials (Finding 1 fix):
  username: Adminmungai  (stored as the user's name field)
  email:    admin@campusconnect.app  (login credential)
  password: Mbatia2000
NOTE: Change these credentials after first login in production.
"""
import os

from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User


def _ensure_columns():
    """Back-fill columns added after the initial schema.

    db.create_all() only creates missing tables — it does not add columns to
    existing tables. This idempotently adds columns introduced in later
    updates (e.g. image_path on marketplace_item / lost_found_item).
    """
    insp = inspect(db.engine)
    existing_tables = set(insp.get_table_names())
    for table, column in (("marketplace_item", "image_path"), ("lost_found_item", "image_path")):
        if table not in existing_tables:
            continue
        cols = {c["name"] for c in insp.get_columns(table)}
        if column not in cols:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(300)"))
            db.session.commit()


def seed_super_admin(app):
    """Seed the super admin user inside the given app context."""
    with app.app_context():
        db.create_all()  # Idempotent — creates tables only if they don't exist
        _ensure_columns()

        if not User.query.filter_by(role="super_admin").first():
            name     = os.environ.get("SUPER_ADMIN_NAME",     "Adminmungai")
            email    = os.environ.get("SUPER_ADMIN_EMAIL",    "admin@campusconnect.app")
            password = os.environ.get("SUPER_ADMIN_PASSWORD", "Mbatia2000")

            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="super_admin",
                active=True,
                institution_id=None,
            )
            db.session.add(user)
            db.session.commit()
            print(f"[seed] Super admin created: {email}")
        else:
            print("[seed] Super admin already exists — skipping.")


if __name__ == "__main__":
    # Standalone script: python seed.py
    # Runs inside a proper Flask app context (Finding 3 fix)
    _app = create_app()
    seed_super_admin(_app)
