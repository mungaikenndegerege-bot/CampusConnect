# CampusConnect setup and development

## Requirements

- Python 3.10 or newer
- pip
- SQLite for local development; PostgreSQL for hosted deployments
- Node.js (optional, for JavaScript syntax checks)

## Install and run locally

```powershell
cd C:\Users\user\Documents\NetBeansProjects\CampusConnect
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For local development, keep `STORAGE_BACKEND=local` and
`DATABASE_URL=sqlite:///campusconnect.db` in `.env`. Set a private
`ADMIN_USERNAME`, a strong `ADMIN_PASSWORD`, and a unique random `SECRET_KEY`.
Then initialize the schema and starter data:

```powershell
python -m flask --app run db upgrade
python seed.py
python run.py
```

The app runs at `http://127.0.0.1:5000`. The `/health` endpoint checks the
database connection.

## Database migrations

The project uses Flask-Migrate/Alembic. After installing dependencies, apply
migrations with:

```powershell
python -m flask --app run db upgrade
```

Run this before `python seed.py`. The initial baseline migration supports a
fresh database and adds the new platform schema to a legacy database without
dropping its existing content. Its downgrade intentionally refuses destructive
rollback; take and verify a database backup before production migrations.

## Environment configuration

The `.env.example` file documents local and Supabase settings. `.env` is local
only and must not be committed.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask signing and content-owner token secret; keep stable and private |
| `DATABASE_URL` | SQLite locally or PostgreSQL in production |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Required administrator login credentials |
| `STORAGE_BACKEND` | `local` for development or `supabase` for hosted storage |
| `SUPABASE_URL` | Supabase project URL, required for Supabase Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only Supabase Storage key; never put in browser code |
| `CORS_ORIGINS` | Optional comma-separated browser origins for a separate frontend |

When using Supabase PostgreSQL, supply its PostgreSQL connection URL. The
application normalizes `postgres://` and `postgresql://` URLs to the psycopg
driver. Keep the Supabase service-role key exclusively in server-side
environment settings.

## Supabase setup

1. Create a Supabase project and configure a database password.
2. Set `DATABASE_URL` to the project's PostgreSQL connection URL.
3. Configure `STORAGE_BACKEND=supabase`, `SUPABASE_URL`, and
   `SUPABASE_SERVICE_ROLE_KEY` in the server environment.
4. Apply the application schema using `python -m flask --app run db upgrade`.
5. Review and run `supabase/migrations/202611230001_rls_and_storage.sql` in the
   Supabase SQL editor only after the application tables exist.
6. Confirm the buckets and policies in Supabase before accepting uploads.

The SQL file configures RLS for direct browser clients. The application uses
its own Flask account/session system, not Supabase Auth; RLS policies do not
map that identity to `auth.uid()`. Normal client operations should use the
Flask API, not direct table access.

## Verification

From the project directory:

```powershell
python -m compileall -q app tests migrations
python -m unittest discover -s tests -v
```

If Node.js is installed, check the JavaScript files:

```powershell
node --check static\js\app.js
node --check static\js\community.js
node --check static\js\marketplace.js
node --check static\js\lostandfound.js
node --check static\js\campus.js
node --check static\js\institutions.js
```

## Local uploads and production limitations

Local development uploads use `static/uploads`. Production Supabase Storage
uses fixed buckets, random object names, extension/size/signature checks, and
signed URLs for private document buckets. These checks are not malware
scanning or complete file-content validation.

Before production use, review the security and service limitations in
[the deployment guide](./DEPLOYMENT.md), including in-process rate limiting,
account authentication, file privacy, and the requirement to execute and
validate database/storage configuration in the actual Supabase project.
