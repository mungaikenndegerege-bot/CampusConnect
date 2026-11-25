# CampusConnect deployment guide

## Status and prerequisites

The repository includes a Render web-service manifest and Supabase-ready
database/storage support. This does not mean that Supabase has been configured
or that the current deployment has been migrated. No live database, storage
project, DNS zone, or production deployment should be changed until the owner
provides the correct credentials and authorizes the operation.

Before deploying, create the Supabase project and Render service, confirm
access to the source repository, and take a verified backup of any existing
production database and uploaded files.

## Supabase configuration

1. Create a Supabase project and keep its database password private.
2. Obtain the PostgreSQL connection URL from Supabase. Use the supported
   connection type for the chosen Render region and connection limits.
3. Configure the Supabase project URL and server-only service-role key.
4. In Render, set the environment values listed below.
5. Apply the app schema with `python -m flask --app run db upgrade` using the
   production environment, via a controlled one-off job or deploy shell.
6. Run `seed.py` only if the institution and advertising placement starter
   records are needed.
7. After the schema exists, review and apply
   `supabase/migrations/202611230001_rls_and_storage.sql` in the Supabase SQL
   editor. Confirm all policies and buckets in the Supabase dashboard.

Do not run a migration against a live database until its target URL has been
confirmed and a backup has been tested. The baseline migration refuses
destructive downgrade; recovery should use a verified backup/restore procedure.

## Render service

The checked-in `render.yaml` configures a Python web service with:

```text
Build:  pip install -r requirements.txt
Start:  gunicorn -w 2 -b 0.0.0.0:$PORT run:app
Health: /health
```

Set these values in the Render service environment:

| Variable | Required value |
|---|---|
| `SECRET_KEY` | Strong, unique secret; keep stable between deploys |
| `DATABASE_URL` | Supabase PostgreSQL connection URL |
| `ADMIN_USERNAME` | Private administrator username |
| `ADMIN_PASSWORD` | Strong, unique administrator password |
| `STORAGE_BACKEND` | `supabase` |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only service-role key |
| `CORS_ORIGINS` | Only if a separate browser frontend needs cross-origin access |

Never put database credentials or the service-role key in the frontend, source
control, issue reports, or screenshots. The Render manifest deliberately
expects environment values for database and Supabase settings.

## Domain and HTTPS

Add a custom domain only after confirming domain ownership. Use the DNS record
type and target shown for this specific service in the Render dashboard; do not
copy guessed or third-party DNS values. Configure the record at the authoritative
DNS provider and wait for Render to validate it and provision HTTPS. Verify the
certificate and redirect behavior before sharing the domain.

## Backups and recovery

- Enable and review the backup/point-in-time recovery options available for the
  selected Supabase plan.
- Keep independent, access-controlled database backups before migrations and
  high-impact moderation or account operations.
- Back up Storage objects separately; a PostgreSQL backup does not include
  uploaded files.
- Periodically verify restoration into a non-production project, including
  database connectivity and representative Storage object retrieval.
- Document retention, encryption, access ownership, and recovery contacts.
- Restore to staging first. Confirm the application schema and files before
  directing production traffic to a restored service.

## Deployment verification

After configuration and deployment:

1. Confirm `/health` returns `{"status":"ok"}`.
2. Check the Render logs for startup, database, and storage errors.
3. Verify feed, institution, marketplace, lost-and-found, event, and
   opportunity reads.
4. Exercise a test post and edit-token flow; confirm Storage uploads and
   signed-document behavior using non-sensitive test files.
5. Confirm administrator login and account suspension controls.
6. Verify that no privileged Supabase key appears in browser source or network
   responses.

## Local validation snapshot

The current local checks passed: Python compilation, all eight focused unit
tests, JavaScript syntax checks, a fresh SQLite migration, and a migration on a
temporary copy of the existing SQLite database. The copied legacy database
retained all three posts and gained the new tables/columns. These checks do not
validate a live Supabase project, Render deployment, custom domain, or
production-scale behavior.

## Security posture and known limitations

This is a deployment foundation, not a fully production-validated service:

- The Supabase migration/RLS SQL has not been validated against a live project.
  Policies limit rows, not individual columns. Public API responses can expose
  poster contact details; review consent and field exposure before production.
- The app uses its own account/password/session implementation, not Supabase
  Auth. Future native clients should use the Flask API unless a deliberate
  shared-auth migration is designed.
- Private-document signed URLs are currently valid for one hour, and public
  API flows can issue them. Do not store sensitive documents in these buckets.
- Rate limiting is in-process memory and is not shared across Gunicorn workers
  or multiple instances. A shared Redis-backed limiter is needed for reliable
  production limits.
- Upload checks validate size, extension, and basic signatures; they do not
  scan for malware or fully decode files.
- Notification delivery, complete moderation/RBAC, shared rate limiting,
  monitoring/error reporting, and load testing remain incomplete.

Treat these limitations as launch gates for public production use.
