# CampusConnect

CampusConnect is a Kenyan student community platform for community discussions,
institution communities, marketplace listings, lost-and-found reports,
announcements, and advertising campaigns. It is implemented as a Flask PWA and
can be installed or used in a mobile or desktop browser.

## Features

- Community feed and topic-based posts
- Image and document attachments
- Post comments and reporting
- Student marketplace listings
- Lost-and-found reports
- Campus events and job/internship opportunities
- Institution directory and institution communities
- Optional student accounts
- Administrator moderation dashboard
- Advertiser registration and campaign management
- Impression, click, placement, and revenue tracking
- Supabase PostgreSQL and Storage configuration for hosted deployments
- Owner edit tokens and idempotent public create requests
- PWA browser installation support

## Documentation

- [User guide](docs/USER-GUIDE.md)
- [Setup and development](docs/SETUP.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [API documentation](docs/API.md)
- [Administrator and moderator guide](docs/ADMIN-GUIDE.md)
- [Advertiser guide](docs/ADVERTISER-GUIDE.md)

## Documentation contents

| Document | Intended reader |
|---|---|
| README | Everyone |
| Setup and development | Developers |
| Deployment guide | Developers and hosting administrators |
| API documentation | Developers and integrators |
| Administrator guide | Moderators and site administrators |
| Advertiser guide | Business users |
| User guide | Students and visitors |

## Technology

- Python 3
- Flask 3
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- SQLite for local development
- PostgreSQL with psycopg supported in deployment
- Supabase Storage adapter with local filesystem support for development
- HTML, CSS, and JavaScript PWA frontend
- Gunicorn for production serving

## Quick start

```powershell
cd C:\Users\user\Documents\NetBeansProjects\CampusConnect
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m flask --app run db upgrade
python seed.py
python run.py
```

Open `http://127.0.0.1:5000`. Health status is available at
`http://127.0.0.1:5000/health`.
Set local `.env` values before starting, including a private admin username
and password. See [setup](docs/SETUP.md) for details.

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask signing and content-owner token secret; use a stable, strong random value |
| `DATABASE_URL` | SQLAlchemy database URL |
| `ADMIN_USERNAME` | CampusConnect administrator username |
| `ADMIN_PASSWORD` | CampusConnect administrator password |
| `STORAGE_BACKEND` | `local` for development or `supabase` for hosted uploads |
| `SUPABASE_URL` | Required when using Supabase Storage |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only key required for Supabase Storage |

For production, set all values through your hosting provider's environment
settings. Never commit secrets or credentials to the repository. Apply schema
changes with `python -m flask --app run db upgrade` before seeding or serving a
new database.

## Production entry point

```text
gunicorn run:app
```

SQLite is suitable for local testing but its filesystem is not durable on all
hosted platforms. Use managed PostgreSQL and configured object storage for a
persistent deployment. Review [the deployment guide](docs/DEPLOYMENT.md) for
migration, RLS, backup, domain, and outstanding production limitations.
