# CampusConnect — Design Review

**Reviewed against:** `02-design.md` (v1.0, 2026-11-11)  
**Requirements source:** `01-requirements.md` (v1.0, 2026-11-11)  
**Reviewer:** Automated design-review agent  
**Repo state:** Greenfield — no existing source code found under `c:\Users\user\Documents\NetBeansProjects\CampusConnect\` (only the `.agents/` pipeline folder exists). All design claims about existing code are therefore unverifiable; they describe code yet to be written.

---

## Findings

### HIGH Severity

---

**Finding 1 — HIGH: Super-admin credentials from the user request are not reflected anywhere in the design**

The original user messages explicitly specified:
> "username will be Adminmungai and password should be Mbatia2000"

The design's seed mechanism (`seed.py`) uses `SUPER_ADMIN_EMAIL` env var defaulting to `admin@campusconnect.app` and `SUPER_ADMIN_PASSWORD` defaulting to `ChangeMe123!`. Neither the name `Adminmungai` nor the password `Mbatia2000` appears. This is a direct conflict with the user's stated requirement.

The `render.yaml` also sets `SUPER_ADMIN_EMAIL: admin@campusconnect.app` and leaves `SUPER_ADMIN_PASSWORD` as `sync: false` (manual entry), so there is no path in the design through which the user-requested credentials get seeded.

**Concrete fix:** Either (a) change the defaults in `seed.py` to use the requested credentials:
```python
name    = os.environ.get("SUPER_ADMIN_NAME",  "Adminmungai")
email   = os.environ.get("SUPER_ADMIN_EMAIL", "admin@campusconnect.app")
password = os.environ.get("SUPER_ADMIN_PASSWORD", "Mbatia2000")
```
and update `render.yaml` accordingly, **or** (b) add a note in the design that the implementer must configure those exact credentials via environment variables and document which variable maps to each. Option (a) is cleaner. Note: the password `Mbatia2000` is weak for production; the design should warn the implementer and prompt the user to change it on first login.

---

**Finding 2 — HIGH: `manifest.json` is served at `/static/manifest.json` but AC-23 and FR-12.1 require it at `/manifest.json`**

The design places `manifest.json` under `static/`:
> `static/manifest.json`

Flask's static file handler serves it at `/static/manifest.json`. The PWA manifest link in `index.html` is not shown explicitly in the design, but AC-23 states it must be reachable at `/manifest.json`. Similarly, `sw.js` is placed at `static/sw.js` and served at `/static/sw.js`, while AC-24 requires `/sw.js`. Browsers also require the service worker to be served from the scope root or a path above the pages it controls; `/static/sw.js` would only control paths under `/static/`, not the whole app.

**Concrete fix:** Either (a) add two explicit Flask routes in `app/__init__.py`:
```python
@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response
```
Or (b) move `manifest.json` and `sw.js` to the `templates/` folder and serve them as Flask routes returning `render_template(...)` with the correct content-type headers. Option (a) is simpler. The design must be updated to specify whichever path is chosen.

---

**Finding 3 — HIGH: `Dockerfile` CMD runs `python seed.py` but `seed.py` calls `create_app()` without a guard — double `db.create_all()` with Gunicorn's 2 workers is a SQLite write-conflict risk**

The Dockerfile CMD is:
```
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:5000 --workers 2 'app:create_app()'"]
```

The design says `run.py` calls `db.create_all()` and `seed_super_admin()`. However `seed.py` as described is a standalone script. If `seed.py` itself calls `create_app()` and `db.create_all()`, this is fine sequentially — but the design does not show the full `seed.py` body; it only shows the `seed_super_admin()` function. It is unspecified whether `seed.py` (the standalone script) calls `create_app()` and `db.create_all()` itself, or whether it imports from somewhere that does.

Additionally, two Gunicorn workers each calling `create_app()` on start-up will not conflict since `db.create_all()` is called inside `create_app()` per the design — `CREATE TABLE IF NOT EXISTS` is idempotent, but concurrent calls on SQLite can produce a `database is locked` error on first boot before the WAL journal is established.

**Concrete fix:** Show the complete `seed.py` body in the design:
```python
# seed.py — run before gunicorn
import os
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def seed_super_admin():
    email    = os.environ.get("SUPER_ADMIN_EMAIL", "admin@campusconnect.app")
    password = os.environ.get("SUPER_ADMIN_PASSWORD", "ChangeMe123!")
    name     = os.environ.get("SUPER_ADMIN_NAME", "Adminmungai")
    if not User.query.filter_by(role="super_admin").first():
        user = User(name=name, email=email,
                    password_hash=generate_password_hash(password),
                    role="super_admin", active=True)
        db.session.add(user)
        db.session.commit()

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_super_admin()
```
Move `db.create_all()` out of `create_app()` and into `seed.py` (run once before Gunicorn). This eliminates the concurrent `create_all` race.

---

**Finding 4 — HIGH: `GET /api/dashboard` does not enforce institution isolation for the super_admin role**

Edge case 5 in the design states:
> "If the caller is `super_admin` and `institution_id` is NULL, the endpoint returns 403."

But `GET /api/dashboard` only has `@jwt_required()` — no role guard is defined for it in the dashboard blueprint section. If a super_admin calls `/api/dashboard`, the design says return 403, but this is never stated as explicit logic in the endpoint description. The design relies on a reader inferring it from Edge Case 5. The same gap exists for every institution-scoped endpoint (`/api/timetable`, `/api/library`, etc.).

**Concrete fix:** Add an explicit guard at the top of every institution-scoped endpoint (or as a Blueprint `before_request` hook):
```python
@dashboard_bp.before_request
@jwt_required()
def check_institution():
    user = get_current_user()
    if user.institution_id is None:
        return {"message": "Super admin must use /api/admin/* routes"}, 403
```
Document this guard pattern in the design so every blueprint implementer knows to include it.

---

### MEDIUM Severity

---

**Finding 5 — MEDIUM: `AC-20` says deactivated-institution users receive HTTP 403 on login, but the design returns 401**

Requirement AC-20:
> "users of that institution subsequently receive HTTP 403 on login"

The Auth Blueprint login flow (step 4) returns:
> `401 "Institution inactive."`

401 and 403 have distinct semantics (unauthenticated vs. forbidden). The requirements doc FR-1.9 says "Deactivated users shall be denied login" without specifying a code, but AC-20 explicitly says 403. The design contradicts AC-20.

**Concrete fix:** Either update AC-20 in the requirements to 401 (more semantically correct — the credentials are valid but the account context is inactive) and document the rationale, or change the design to return 403 for inactive institution. The design should state the chosen code and explain it. Recommend keeping 401 and correcting AC-20, since 403 implies the server understood and refused, which is accurate — but 401 is the conventional "cannot authenticate" response and is what most clients expect from a login endpoint. Pick one and state it explicitly.

---

**Finding 6 — MEDIUM: The `roles_required` decorator and `@jwt_required()` are applied in the wrong order — this will raise a runtime error**

The design shows:
```python
def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            ...
```

This nests `@jwt_required()` *inside* `roles_required`. That means `roles_required` does not itself call `jwt_required`; the JWT check only fires when `wrapper` is called — which is correct. However, the design elsewhere also shows endpoint examples calling both decorators simultaneously, e.g. the blueprint sections describe endpoints as `@roles_required(...)` with no additional `@jwt_required()`. This is fine as written — `roles_required` already wraps `jwt_required`.

The real problem: `get_jwt()` called inside `wrapper` relies on the Flask-JWT-Extended request context that `@jwt_required()` sets up. If `roles_required` is ever used *without* the inner `@jwt_required()` (e.g. a developer forgets that `roles_required` already includes it and also adds an outer `@jwt_required()`), the double-decoration silently works. But if someone uses `get_jwt()` outside the decorator, it fails. This is a design clarity problem.

**Concrete fix:** Rename the decorator to make it self-documenting and add a comment:
```python
def roles_required(*roles):
    """
    Decorator that BOTH enforces JWT authentication AND checks role.
    Do NOT also add @jwt_required() on the same route — it is already included.
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get("role") not in roles:
                return {"message": "Forbidden"}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```
Add this documentation note to the design.

---

**Finding 7 — MEDIUM: Library `DELETE` has a race condition — file is deleted from DB first, then disk; a crash between the two leaves an orphaned file on disk with no record**

The design says:
> "After DB delete, attempt `os.remove(file_path)` — log warning if file missing on disk but do not fail."

The DB delete is committed *before* the disk delete. If the process crashes after the commit but before `os.remove`, the file is orphaned forever (no record to find it). The reverse order (disk first, then DB) means a crash leaves a dangling DB record pointing to a missing file — which the download endpoint already handles gracefully (404).

**Concrete fix:** Reverse the order — delete the file from disk first, then commit the DB record deletion:
```python
# 1. Remove from disk first (recoverable: DB record still exists on crash)
try:
    os.remove(file_path)
except FileNotFoundError:
    pass  # already gone, continue
# 2. Now delete DB record and commit
db.session.delete(library_file)
db.session.commit()
```
Document this ordering decision in the design.

---

**Finding 8 — MEDIUM: The `GET /api/dashboard` `upcoming_assignments` query annotates completion for students only, but the design does not specify what the endpoint returns for lecturers/admins calling it**

The design says:
> "Each is annotated with `completed: bool` by joining `AssignmentCompletion` for the current student."

A lecturer or institution admin will also have a valid JWT and can call `GET /api/dashboard`. The design does not say whether `completed` is omitted, always `false`, or the endpoint is restricted to students. Similarly, for `today_classes` a super admin calling the endpoint would receive a 403 (per edge case 5), but for lecturers viewing their own dashboard the behaviour is fully unspecified beyond the query returning institution-scoped data.

**Concrete fix:** Add a role-differentiation note to the dashboard spec:
- For `student` callers: include `completed` and `overdue` per assignment.
- For `lecturer` / `institution_admin` callers: omit `completed`; optionally include completion count per assignment (count of students who marked done).
- For `super_admin`: return 403 (as stated in edge case 5, but now explicit in the endpoint spec).

---

**Finding 9 — MEDIUM: SQLite with 2 Gunicorn workers and write-heavy endpoints is a correctness hazard not adequately addressed**

The design mentions SQLite's "single-writer semantics" in the Dockerfile note but does not prescribe WAL mode or connection timeout settings. With 2 workers, concurrent POST requests (marketplace listings, community posts, file uploads) will cause `sqlite3.OperationalError: database is locked` errors that propagate as 500s to the client. This is a reliability defect, not just a performance note.

**Concrete fix:** Add to `config.py` or the app factory:
```python
# Enable WAL mode and a busy timeout to handle concurrent workers
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, conn_record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
```
Document this in the design under Configuration or Deployment.

---

**Finding 10 — MEDIUM: `POST /api/auth/register` accepts `role` from the caller but only allows `student` or `lecturer` — there is no institution-admin registration path defined**

The design says `institution_admin` accounts are added by the super admin via `POST /api/admin/my/users` (which is actually an institution-admin route, not a super-admin route). But there is no endpoint to create the *first* institution admin for a newly created institution. The super admin creates institutions, but the design shows no route for the super admin to then assign an institution_admin user to that institution.

Looking at the admin blueprint: `POST /api/admin/my/users` is an **institution-admin** route (it uses the caller's own `institution_id`). The super-admin routes (`/api/admin/institutions`, `/api/admin/users`, `/api/admin/stats`) have no POST for creating users.

**Concrete fix:** Add a super-admin user-creation endpoint:
```
POST /api/admin/users   (super_admin only)
Body: { name, email, password, role, institution_id }
role may be: institution_admin | lecturer | student
```
Or, document that after creating an institution, the super admin promotes a user to institution_admin via `PATCH /api/admin/users/<id>` — but that endpoint doesn't exist either. The design must specify how the first institution_admin for each institution gets created.

---

**Finding 11 — MEDIUM: `GET /api/library` pagination uses `?page=1&per_page=20` but the endpoint description does not specify what field results are ordered by**

Every other paginated list endpoint specifies an `ORDER BY` clause (assignments: `due_date ASC`; announcements: `pinned DESC, created_at DESC`; marketplace: unspecified — see Finding 12). Library's `GET` section only says "Returns paginated list with metadata" with no ordering defined.

**Concrete fix:** Add: "Results are ordered by `created_at DESC` (newest first)." to the Library GET spec.

---

**Finding 12 — MEDIUM: `GET /api/marketplace/items` has no defined default sort order**

The marketplace GET spec specifies query params `?category=&sold=false&page=1&per_page=20` but never states how results are ordered. Without a stable ordering, pagination is non-deterministic (items may appear on multiple pages or be skipped when new listings are created).

**Concrete fix:** Add: "Results are ordered by `created_at DESC`." to the marketplace GET spec.

---

**Finding 13 — MEDIUM: Input validation is missing for `price` in `POST /api/marketplace/items` — no upper bound or type coercion rule**

The validation spec says `price` must be "numeric ≥ 0". There is no maximum value, no rule about how many decimal places are accepted, and no rule about what to do if the client sends a string like `"free"` or `"1,000"`. `float` in Python will accept `float("inf")`.

**Concrete fix:** Add:
- `price` must be a JSON number (not a string) or coercible to float without error.
- `0 ≤ price ≤ 1,000,000` (or a reasonable upper bound for the marketplace context).
- Round to 2 decimal places before storing: `round(float(price), 2)`.
- If `float(price)` raises `ValueError` → 400 "price must be a number".

---

**Finding 14 — MEDIUM: The `community.py` "one level of nesting" rule validation is incomplete**

The design says:
> "`parent_id` (optional FK to comment on same post — validated to be on this post and to have no existing parent, enforcing one level of nesting)"

The check "has no existing parent" is applied to the *parent comment*, meaning: "the comment I'm replying to must not itself be a reply." This is correct for one-level nesting. However, the design does not specify what HTTP code and message to return when this rule is violated, nor does it specify what happens to nested comments when the top-level parent is deleted (cascade).

**Concrete fix:** Add:
- If `parent_id` refers to a comment that itself has a `parent_id` → 400 "Cannot reply to a reply; only one level of nesting is supported."
- When a top-level comment is deleted, its replies are cascade-deleted via `cascade="all, delete-orphan"` on `CommunityComment.replies` relationship (this needs to be on the model — the design only shows `cascade` on `CommunityPost→CommunityComment`, not on the self-referential `CommunityComment→CommunityComment`).

---

**Finding 15 — MEDIUM: `date_occurred` for Lost & Found is validated as "not in the future" but no maximum past date is specified — could accept obviously invalid dates**

The design says:
> "`date_occurred` (required, ISO date, not in the future)"

There is no lower bound. A user could submit `date_occurred: "1900-01-01"`. While not a security issue, it is a data quality problem. More importantly, the design does not specify the HTTP response when `date_occurred` is in the future.

**Concrete fix:** Add: "If `date_occurred > date.today()` → 400 'Date occurred cannot be in the future.'" and optionally "If `date_occurred < date.today() - timedelta(days=365)` → 400 'Date occurred cannot be more than one year in the past.'" Document the chosen constraint.

---

### NIT Severity

---

**Finding 16 — NIT: `User.query.get_or_404(user_id)` is deprecated in SQLAlchemy 2.x / Flask-SQLAlchemy 3.x**

The `get_current_user()` helper uses `User.query.get_or_404(user_id)`. In Flask-SQLAlchemy 3.x (which the design specifies), `Query.get()` is deprecated. The correct form is:
```python
db.session.get(User, user_id) or abort(404)
```

---

**Finding 17 — NIT: `datetime.utcnow` is deprecated in Python 3.12+**

The design specifies `datetime.utcnow` for all timestamps. Python 3.12 deprecates `datetime.utcnow()` in favour of `datetime.now(timezone.utc)`. Although the design targets Python 3.11-slim (where it still works), models using `default=datetime.utcnow` will trigger deprecation warnings and break on a future Python upgrade. Prefer `default=lambda: datetime.now(timezone.utc)` now.

---

**Finding 18 — NIT: `requirements.txt` has no `itsdangerous` or `click` pin, which are transitive Flask deps that sometimes break**

Flask 3.x depends on `itsdangerous` and `click`. Pinning only direct dependencies is acceptable for reproducibility if `pip-compile` / lock files are used, but `requirements.txt` as shown has no lock file. Consider adding a comment or a `requirements.in` / `pip-tools` note.

---

**Finding 19 — NIT: The service worker `SHELL_ASSETS` list includes a placeholder comment `/* all other JS modules */` — this is not implementable as-is**

The `sw.js` snippet reads:
```javascript
const SHELL_ASSETS = ["/", "/static/css/style.css", "/static/js/app.js",
  /* all other JS modules */, "/static/manifest.json"];
```
The implementer must enumerate all JS module paths explicitly. The comment leaves ambiguity.

**Concrete fix:** List all paths:
```javascript
const SHELL_ASSETS = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/auth.js",
  "/static/js/dashboard.js",
  "/static/js/timetable.js",
  "/static/js/library.js",
  "/static/js/announcements.js",
  "/static/js/assignments.js",
  "/static/js/community.js",
  "/static/js/marketplace.js",
  "/static/js/lostandfound.js",
  "/static/js/admin.js",
  "/static/manifest.json"
];
```

---

**Finding 20 — NIT: The `Dockerfile` does not include `--timeout 120` in the documented CMD**

The design body says:
> "`--timeout 120` is added to handle large file uploads"

But the `Dockerfile` CMD shown is:
```
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:5000 --workers 2 'app:create_app()'"]
```
`--timeout 120` is missing from the Dockerfile CMD (it appears only in `render.yaml`'s `startCommand`). These two should match.

---

**Finding 21 — NIT: The `GET /api/dashboard` `today_classes` query uses `datetime.utcnow().strftime("%a")` which produces locale-dependent output on some systems**

`strftime("%a")` produces abbreviated weekday names in the system locale (e.g., "Mon" in English but "Lun" in French). The design stores days as `Mon|Tue|Wed|Thu|Fri|Sat|Sun`. If the server's locale is not English, the query will return zero results every day.

**Concrete fix:** Use the locale-independent `calendar.day_abbr` or a manual mapping:
```python
DAY_ABBR = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
today_abbrev = DAY_ABBR[datetime.utcnow().weekday()]
```

---

**Finding 22 — NIT: FR-2.4 requires quick-link navigation buttons on the dashboard but the dashboard endpoint (`GET /api/dashboard`) returns no data to drive them; this is a pure frontend concern not addressed in the JS module spec**

FR-2.4: "The dashboard shall provide quick-link navigation buttons to Timetable, Library, Community, Marketplace, and Lost & Found."

The design's `dashboard.js` module section only describes consuming the `/api/dashboard` response. There is no mention of rendering the quick-link buttons. This is a UI-only item, but it needs to appear in the `dashboard.js` frontend spec so the implementer knows to add it.

---

## Verified Assumptions

The following design claims were checked against the repo. Since the repository is **completely greenfield** (no source files exist), the design is describing code to be written, not code that already exists. The following structural/technology claims are verifiable against the stated library versions and Flask/SQLAlchemy documentation:

- **Flask 3.x Blueprint registration pattern** — the `create_app()` factory with `app.register_blueprint()` is the correct Flask 3.x pattern. ✓
- **Flask-JWT-Extended 4.x `get_jwt()` / `get_jwt_identity()`** — these are the correct function names for v4.x. ✓
- **Werkzeug `generate_password_hash` / `check_password_hash`** — available in Werkzeug 3.x (shipped with Flask 3.x). ✓
- **Flask `send_from_directory`** — correct function for serving files from a directory path. ✓
- **Flask-CORS `resources={r"/api/*": {"origins": "*"}}`** — valid Flask-CORS 4.x configuration. ✓
- **`MAX_CONTENT_LENGTH` enforces 413 automatically** — Flask does enforce this for request body size; however, see Finding below on streaming uploads. ✓ for standard uploads.
- **SQLAlchemy unique constraint syntax** — `UniqueConstraint('institution_id', 'code')` is valid SQLAlchemy syntax. ✓
- **Gunicorn `'app:create_app()'` callable syntax** — valid Gunicorn application factory syntax. ✓
- **`python:3.11-slim` Docker base image** — exists and is actively maintained. ✓
- **`render.yaml` `type: web` service with `plan: free`** — valid Render Blueprint syntax for a web service. ✓
- **PWA `display: standalone` in manifest** — correct value for installable PWA. ✓
- **Service worker `fetch` event with `request.url.includes("/api/")`** — valid, though note `includes` is a substring match; a URL like `/static/api-docs.html` would accidentally be treated as an API call. Acceptable for v1. ✓

---

## Unverified / Wrong Assumptions

1. **"Flask's `@app.errorhandler(Exception)` catches unhandled exceptions"** — This is partially correct. Flask's `errorhandler(Exception)` catches exceptions that propagate out of view functions in production mode, but in debug mode Flask re-raises them. The design should note that this handler is only active when `FLASK_ENV=production` (or `app.debug=False`). The implementer must not accidentally run with `debug=True` in Docker. The design does not show how `debug` mode is set/disabled.

2. **"Static files (`/static/...`) are served by Flask's built-in static handler before the catch-all fires"** — Correct only if the static folder is configured and Flask's default static URL (`/static`) matches. The app factory sets `static_folder="../static"` which moves the actual folder but keeps the URL prefix at `/static`. This is correct. ✓ — but the catch-all `/<path:path>` will also match `/static/something` paths. Flask's static handler fires *before* view functions because it is registered as a Werkzeug rule, so this claim is correct. ✓

3. **"The `seed.py` function runs inside an `app.app_context()`"** — The design shows the `seed_super_admin()` function body but not the surrounding script that creates the app context. This is unverified (see Finding 3). The implementer could omit the `app_context()` wrapper, causing `RuntimeError: No application found`.

4. **"Icon PNGs (192×192 and 512×512) are generated as simple purple squares with 'CC' text as SVG-to-PNG data URIs embedded in the HTML, or as static PNG files committed to the repo"** — This is internally contradictory ("or as..."). The manifest references `/static/icons/icon-192.png` and `/static/icons/icon-512.png` as files. SVG-to-PNG data URIs in HTML cannot satisfy a manifest `icons` array (manifests reference URLs, not data URIs). The correct approach is to commit actual PNG files. The design gives the implementer a false option.

5. **"`SUPER_ADMIN_PASSWORD` is set manually in Render dashboard"** — `render.yaml` sets `sync: false`, which in Render means the value is not stored in the YAML and must be set via the Render dashboard. This is correct Render behaviour. ✓ — but the design does not document *where* the user should set it (Render Dashboard > Environment > Add variable) or warn that the service will start with no password if not set, potentially causing the seed to use the default `ChangeMe123!`.

---

## Verdict

| Severity | Count |
|---|---|
| HIGH | 4 |
| MEDIUM | 11 |
| NIT | 7 |

**VERDICT: CHANGES_REQUESTED**

There are 4 HIGH findings and 11 MEDIUM findings. The most critical are:
1. The user-requested super-admin credentials (`Adminmungai` / `Mbatia2000`) are not wired up anywhere in the design.
2. `manifest.json` and `sw.js` are served at the wrong paths for PWA compliance.
3. `seed.py` is incompletely specified — the app context wrapper is missing.
4. Institution-scoped endpoint isolation for super_admin is documented only as an edge-case note rather than explicit enforced logic.

Address the HIGH and MEDIUM findings and resubmit for review.
