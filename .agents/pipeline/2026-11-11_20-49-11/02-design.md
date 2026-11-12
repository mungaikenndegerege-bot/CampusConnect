# CampusConnect — Technical Design

**Version:** 1.0  
**Date:** 2026-11-11  
**Stack:** Python 3.11 · Flask · SQLAlchemy · SQLite · Vanilla JS SPA · PWA · Render (Docker)

---

## Overview

CampusConnect is a single-container web application. Flask serves both a JSON REST API (under `/api/`) and the static SPA shell (`index.html` + assets). The frontend is a client-side-rendered single-page app written in plain ES6+ JS, broken into per-feature modules that swap the main content area when the user navigates. SQLite is the database via Flask-SQLAlchemy. Authentication uses Flask-JWT-Extended with 24-hour access tokens stored in `localStorage`. All feature domains are implemented as Flask Blueprints registered in an app factory. The project lives at `c:\Users\user\Documents\NetBeansProjects\CampusConnect\` and is deployed to Render as a Docker container running Gunicorn.

---

## Technology Stack (locked)

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11 | Requested; 3.11-slim is a small Docker base |
| Web framework | Flask 3.x | Lightweight, Blueprint-friendly |
| ORM | Flask-SQLAlchemy 3.x | Integrates with Flask app context |
| Database | SQLite (file: `campusconnect.db`) | Zero-config, Render-compatible for v1 |
| Auth | Flask-JWT-Extended 4.x | JWT access tokens, decorators for RBAC |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` | Already a Flask dependency |
| CORS | Flask-CORS | Required for local dev; same-origin in prod |
| File serving | Flask `send_from_directory` | Serves uploaded files from `static/uploads/` |
| WSGI server | Gunicorn 21.x | Production server in Docker |
| Config | python-dotenv | Loads `.env` for local dev |
| Frontend | Vanilla JS (ES6 modules), HTML5, CSS3 | As specified; no build step |
| PWA | `manifest.json` + `sw.js` Cache API | Installability and offline shell |
| Deployment | Docker (`python:3.11-slim`) + Render | As specified |

---

## Project Structure

```
CampusConnect/
├── app/
│   ├── __init__.py          # app factory: create_app()
│   ├── models.py            # all SQLAlchemy models
│   ├── auth.py              # Blueprint: /api/auth
│   ├── dashboard.py         # Blueprint: /api/dashboard
│   ├── timetable.py         # Blueprint: /api/timetable
│   ├── library.py           # Blueprint: /api/library
│   ├── announcements.py     # Blueprint: /api/announcements
│   ├── assignments.py       # Blueprint: /api/assignments
│   ├── community.py         # Blueprint: /api/community
│   ├── marketplace.py       # Blueprint: /api/marketplace
│   ├── lostandfound.py      # Blueprint: /api/lostandfound
│   └── admin.py             # Blueprint: /api/admin
├── static/
│   ├── manifest.json
│   ├── sw.js
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js           # router, nav, auth state
│   │   ├── auth.js          # login/register screens
│   │   ├── dashboard.js
│   │   ├── timetable.js
│   │   ├── library.js
│   │   ├── announcements.js
│   │   ├── assignments.js
│   │   ├── community.js
│   │   ├── marketplace.js
│   │   ├── lostandfound.js
│   │   └── admin.js
│   └── uploads/             # uploaded library files (gitignored)
├── templates/
│   └── index.html           # single HTML shell
├── config.py
├── run.py
├── seed.py                  # seeds super_admin on first run
├── requirements.txt
├── Dockerfile
├── render.yaml
└── .gitignore
```

---

## Configuration (`config.py`)

```python
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///campusconnect.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024   # 20 MB hard limit enforced by Flask
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}
```

`run.py` calls `create_app()`, calls `db.create_all()`, calls `seed_super_admin()`, then starts Flask's dev server on port 5000. Gunicorn in Docker calls `create_app()` via `app:create_app()`.

---

## App Factory (`app/__init__.py`)

```python
def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(Config)
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    from .auth import auth_bp
    # ... register all blueprints ...
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        return render_template("index.html")

    return app
```

The catch-all route returns `index.html` for any non-`/api/` path, enabling client-side routing. Static files (`/static/...`) are served by Flask's built-in static handler before the catch-all fires.

---

## Database Models (`app/models.py`)

All models use `db = SQLAlchemy()` imported from `app/__init__.py`. Timestamps use `datetime.utcnow`.

### Institution
```
id (PK), name (str, unique), code (str, unique), logo_url (str, nullable),
active (bool, default True), created_at (datetime)
```

### User
```
id (PK), institution_id (FK→Institution, nullable for super_admin),
name (str), email (str, unique), password_hash (str),
role (str: super_admin|institution_admin|lecturer|student),
active (bool, default True), created_at (datetime)
```
Index: `(institution_id, role)` for fast admin queries.

### Course
```
id (PK), institution_id (FK→Institution), name (str), code (str),
lecturer_id (FK→User, nullable)
Unique constraint: (institution_id, code)
```

### TimetableSlot
```
id (PK), institution_id (FK), course_id (FK→Course),
day_of_week (str: Mon|Tue|Wed|Thu|Fri|Sat|Sun),
start_time (str: "HH:MM"), end_time (str: "HH:MM"),
room (str, nullable), color (str, default "#6C3CE1")
```
Time stored as strings (HH:MM) to avoid timezone complexity; validation is in the API layer.

### LibraryFile
```
id (PK), institution_id (FK), course_id (FK→Course),
uploaded_by (FK→User), title (str), description (str, nullable),
category (str: Notes|Past Papers|Learning Materials|Course Documents),
filename (str), file_path (str), created_at (datetime)
```

### Announcement
```
id (PK), institution_id (FK), posted_by (FK→User),
title (str), body (text), pinned (bool, default False), created_at (datetime)
```

### Assignment
```
id (PK), institution_id (FK), course_id (FK→Course),
created_by (FK→User), title (str), description (str, nullable),
due_date (date), created_at (datetime)
```

### AssignmentCompletion
```
id (PK), assignment_id (FK→Assignment), student_id (FK→User),
completed_at (datetime)
Unique constraint: (assignment_id, student_id)
```

### CommunityPost
```
id (PK), institution_id (FK), author_id (FK→User),
title (str), body (text),
topic (str: General|Academic|Study Groups|Q&A),
likes (int, default 0), created_at (datetime)
```

### CommunityComment
```
id (PK), post_id (FK→CommunityPost), author_id (FK→User),
parent_id (FK→CommunityComment, nullable — for one level of nesting),
body (text), created_at (datetime)
```

### MarketplaceItem
```
id (PK), institution_id (FK), seller_id (FK→User),
title (str), description (str, nullable), price (float),
category (str: Books|Electronics|Accessories|Accommodation|Other),
contact (str), sold (bool, default False), created_at (datetime)
```

### LostFoundItem
```
id (PK), institution_id (FK), posted_by (FK→User),
item_type (str: lost|found), title (str), description (str, nullable),
location (str, nullable), date_occurred (date),
contact (str), resolved (bool, default False), created_at (datetime)
```

---

## Authentication Blueprint (`app/auth.py`)

**Endpoints:**

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | None | Register student or lecturer |
| POST | `/api/auth/login` | None | Login, returns JWT |
| GET | `/api/auth/me` | JWT | Current user profile |

**Register flow:**
1. Accept: `name`, `email`, `password`, `institution_id`, `role` (only `student` or `lecturer` allowed from public registration).
2. Validate all required fields present; email format check with a simple regex; password ≥ 8 chars.
3. Check `institution_id` exists and is active → 400 if not.
4. Check email uniqueness → 409 if taken.
5. Hash password with `generate_password_hash`.
6. Create `User` with `active=True`. Commit. Return 201 + JWT.

**Login flow:**
1. Accept: `email`, `password`.
2. Look up user by email. If not found → 401 (generic message, do not confirm existence).
3. If `user.active == False` → 401 "Account deactivated."
4. If `user.institution` exists and `user.institution.active == False` → 401 "Institution inactive."
5. `check_password_hash` → 401 on mismatch.
6. Create access token with identity = `user.id`, additional claims: `role`, `institution_id`.
7. Return 200 + `{ "access_token": "...", "user": { id, name, email, role, institution_id } }`.

**RBAC decorator pattern** (defined in `app/auth.py`, imported by all blueprints):
```python
def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims["role"] not in roles:
                return {"message": "Forbidden"}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

**Institution isolation helper** (also in `app/auth.py`):
```python
def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get_or_404(user_id)
```
Every endpoint that accesses institution-scoped data calls `get_current_user()` and filters all queries by `institution_id = current_user.institution_id`. This is enforced in every blueprint; there is no trust in the frontend.

---

## Dashboard Blueprint (`app/dashboard.py`)

**Endpoint:** `GET /api/dashboard` — `@jwt_required()`

Returns a single JSON object built from four sub-queries:

```json
{
  "today_classes": [ TimetableSlot... ],
  "upcoming_assignments": [ Assignment... ],
  "announcements": [ Announcement... ],
  "user": { name, role, institution_name }
}
```

- `today_classes`: `TimetableSlot.query.filter_by(institution_id=..., day_of_week=today_abbrev)`. `today_abbrev` derived from `datetime.utcnow().strftime("%a")` → "Mon", "Tue", etc.
- `upcoming_assignments`: `Assignment.query.filter(institution_id=..., due_date >= today).order_by(due_date).limit(5)`. Each is annotated with `completed: bool` by joining `AssignmentCompletion` for the current student.
- `announcements`: `Announcement.query.filter_by(institution_id=...).order_by(pinned.desc(), created_at.desc()).limit(3)`.

Error handling: if the JWT identity resolves to a deleted user (edge case after account deletion), return 404.

---

## Timetable Blueprint (`app/timetable.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/timetable` | All institution roles |
| POST | `/api/timetable` | lecturer, institution_admin |
| PUT | `/api/timetable/<id>` | lecturer, institution_admin |
| DELETE | `/api/timetable/<id>` | lecturer, institution_admin |

`GET` returns all slots for the user's institution, grouped by day: `{ "Mon": [...], "Tue": [...], ... }`.

**Create/Update validation:**
- `course_id`: required, must exist in same institution → 400 if not.
- `day_of_week`: must be one of `["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]` → 400.
- `start_time` / `end_time`: must match `^([01]\d|2[0-3]):[0-5]\d$` → 400.
- `start_time` < `end_time` → 400 if violated.
- `color`: optional, must match `^#[0-9A-Fa-f]{6}$` or be omitted; defaults to `#6C3CE1`.

**Delete:** Verify slot belongs to current user's institution → 404 if not found, 403 if wrong institution.

---

## Library Blueprint (`app/library.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/library` | All institution roles |
| POST | `/api/library/upload` | lecturer |
| GET | `/api/library/<id>/download` | All institution roles |
| DELETE | `/api/library/<id>` | lecturer (own), institution_admin (any) |

**Upload:**
1. Receive multipart form: `file`, `title`, `course_id`, `category`, `description` (optional).
2. Validate file present → 400.
3. Extension check: `filename.rsplit(".", 1)[-1].lower()` in `ALLOWED_EXTENSIONS` → 415 if not.
4. MIME type check using `file.content_type` — must be `application/pdf`, `application/msword`, or `application/vnd.openxmlformats-officedocument.wordprocessingml.document` → 415.
5. Flask enforces `MAX_CONTENT_LENGTH = 20 MB` → returns 413 automatically.
6. `course_id` must belong to same institution → 400.
7. `category` must be one of the four valid values → 400.
8. Generate a UUID-based safe filename: `str(uuid4()) + "." + ext`. Save to `UPLOAD_FOLDER`.
9. If `os.makedirs` or `file.save()` fails → log error, return 500 "File save failed."
10. Create `LibraryFile` record. Commit. Return 201 + metadata.

**Download:** `send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)`. Institution check: `LibraryFile.institution_id == current_user.institution_id` → 403 if mismatch. File not found on disk → 404.

**Delete:** Lecturer may only delete their own files (`uploaded_by == current_user.id`). Institution admin may delete any. After DB delete, attempt `os.remove(file_path)` — log warning if file missing on disk but do not fail.

**GET list:** Supports query params `?course_id=&category=&page=1&per_page=20`. Returns paginated list with metadata.

---

## Announcements Blueprint (`app/announcements.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/announcements` | All institution roles |
| POST | `/api/announcements` | institution_admin, lecturer |
| PATCH | `/api/announcements/<id>` | institution_admin (any), lecturer (own) |
| DELETE | `/api/announcements/<id>` | institution_admin (any), lecturer (own) |

**GET:** Returns announcements for `institution_id`, ordered by `pinned DESC, created_at DESC`. Pagination: `?page=1&per_page=20`.

**POST validation:** `title` (required, ≤ 200 chars), `body` (required, ≤ 5000 chars). `pinned` optional bool, defaults to False.

**PATCH:** Accepts `title`, `body`, `pinned` (all optional). Lecturers patching an announcement they did not author → 403.

**DELETE:** Lecturer deleting another author's announcement → 403. Institution admin may delete any in their institution.

---

## Assignments Blueprint (`app/assignments.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/assignments` | All institution roles |
| POST | `/api/assignments` | lecturer, institution_admin |
| PUT | `/api/assignments/<id>` | lecturer (own), institution_admin (any) |
| DELETE | `/api/assignments/<id>` | lecturer (own), institution_admin (any) |
| POST | `/api/assignments/<id>/complete` | student |

**GET:** Returns assignments for institution, ordered by `due_date ASC`. Query params: `?course_id=&page=1&per_page=20`. For student callers, each assignment includes `completed: bool` and `overdue: bool`. `overdue = due_date < date.today() and not completed`.

**POST validation:** `title` (required, ≤ 200 chars), `due_date` (required, ISO format `YYYY-MM-DD`, must be a valid date), `course_id` (required, must belong to institution). `description` optional ≤ 2000 chars.

**Complete endpoint:**
- Verify assignment belongs to current institution → 403/404.
- Check `AssignmentCompletion` unique constraint: if already exists → 409 "Already marked complete."
- Create record. Return 201.

---

## Community Blueprint (`app/community.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/community/posts` | All institution roles |
| POST | `/api/community/posts` | All institution roles |
| GET | `/api/community/posts/<id>` | All institution roles |
| DELETE | `/api/community/posts/<id>` | author, institution_admin |
| POST | `/api/community/posts/<id>/comments` | All institution roles |
| DELETE | `/api/community/posts/<id>/comments/<cid>` | comment author, institution_admin |
| POST | `/api/community/posts/<id>/like` | All institution roles |

**GET posts:** Query params `?topic=&page=1&per_page=20`. Returns posts with `author_name`, `comment_count`, `likes`. Institution-scoped.

**POST post validation:** `title` (required, ≤ 200 chars), `body` (required, ≤ 10 000 chars), `topic` (required, one of the four valid values).

**GET single post:** Returns full post + all comments (top-level + replies nested under their parent). Institution check on the post.

**Comment validation:** `body` (required, ≤ 2000 chars), `parent_id` (optional FK to comment on same post — validated to be on this post and to have no existing parent, enforcing one level of nesting).

**Like:** Simple `UPDATE CommunityPost SET likes = likes + 1`. No per-user deduplication in v1 (documented assumption).

**Delete post:** Cascades delete to `CommunityComment` via SQLAlchemy `cascade="all, delete-orphan"` on the relationship.

---

## Marketplace Blueprint (`app/marketplace.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/marketplace/items` | All institution roles |
| POST | `/api/marketplace/items` | All institution roles |
| PATCH | `/api/marketplace/items/<id>` | seller, institution_admin |
| DELETE | `/api/marketplace/items/<id>` | seller, institution_admin |

**POST validation:** `title` (required, ≤ 200 chars), `price` (required, numeric ≥ 0), `category` (required, one of five valid values), `contact` (required, ≤ 200 chars). `description` optional ≤ 2000 chars.

**PATCH:** Accepts `sold` (bool), `title`, `description`, `price`, `category`, `contact`. Non-seller non-admin trying to patch → 403. `sold` is the primary use case; full edit is also supported.

**GET:** Query params `?category=&sold=false&page=1&per_page=20`. Institution-scoped.

---

## Lost & Found Blueprint (`app/lostandfound.py`)

| Method | Path | Roles |
|---|---|---|
| GET | `/api/lostandfound` | All institution roles |
| POST | `/api/lostandfound` | All institution roles |
| PATCH | `/api/lostandfound/<id>` | poster, institution_admin |
| DELETE | `/api/lostandfound/<id>` | poster, institution_admin |

**POST validation:** `item_type` (required, `lost` or `found`), `title` (required, ≤ 200 chars), `date_occurred` (required, ISO date, not in the future), `contact` (required, ≤ 200 chars). `description`, `location` optional.

**PATCH:** Accepts `resolved` (bool), and all mutable fields. Ownership check same pattern as Marketplace.

**GET:** Query params `?item_type=&resolved=false&page=1&per_page=20`. Institution-scoped, ordered by `created_at DESC`.

---

## Admin Blueprint (`app/admin.py`)

This blueprint handles both super-admin and institution-admin operations, with RBAC separating access.

### Super Admin routes

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/institutions` | List all institutions |
| POST | `/api/admin/institutions` | Create institution |
| PATCH | `/api/admin/institutions/<id>` | Edit / activate / deactivate |
| GET | `/api/admin/users` | All users, all institutions |
| GET | `/api/admin/stats` | Platform-wide stats |

**Create institution:** `name` (required, unique), `code` (required, unique, ≤ 20 chars uppercase), `logo_url` (optional). Returns 409 if name or code already exists.

**Deactivate:** `PATCH` with `active: false` sets `Institution.active = False`. Login check in auth blueprint reads institution active status (described in Auth section).

**Stats:** Returns counts: `institutions`, `users_by_role` (dict), `library_files`, `community_posts`.

### Institution Admin routes

| Method | Path | Description |
|---|---|---|
| GET | `/api/admin/my/users` | Users in own institution |
| POST | `/api/admin/my/users` | Add student or lecturer |
| PATCH | `/api/admin/my/users/<id>` | Activate / deactivate |
| GET | `/api/admin/my/courses` | Courses in own institution |
| POST | `/api/admin/my/courses` | Create course |
| PUT | `/api/admin/my/courses/<id>` | Edit course |
| DELETE | `/api/admin/my/courses/<id>` | Delete course |

**Add user:** `name`, `email`, `password`, `role` (only `student` or `lecturer` allowed). Hashes password immediately. Returns 409 on duplicate email.

**Add course:** `name` (required), `code` (required), `lecturer_id` (optional — must be a lecturer in same institution). Unique `(institution_id, code)` enforced at DB level; return 409 on duplicate.

---

## Standard API Response Format

All endpoints return JSON. Success:
```json
{ "data": <payload>, "message": "OK" }
```
Error:
```json
{ "message": "Human-readable error description" }
```
Paginated lists:
```json
{
  "data": [...],
  "pagination": { "page": 1, "per_page": 20, "total": 142, "pages": 8 },
  "message": "OK"
}
```
HTTP status codes used: 200, 201, 400 (validation), 401 (unauthenticated), 403 (forbidden), 404, 409 (conflict), 413 (file too large), 415 (unsupported media), 500.

---

## Error Handling Summary

| Situation | HTTP Code | Recoverable | Logged |
|---|---|---|---|
| Missing required field | 400 | Yes — fix input | No |
| Invalid field value | 400 | Yes — fix input | No |
| Email already exists | 409 | Yes — use different email | No |
| Wrong credentials | 401 | Yes — retry | No |
| Inactive user/institution | 401 | No — contact admin | No |
| Missing JWT | 401 | Yes — login | No |
| Wrong role | 403 | No | No |
| Cross-institution access | 403 | No | Yes (warning) |
| Resource not found | 404 | Yes — check ID | No |
| File too large | 413 | Yes — reduce size | No |
| Wrong file type | 415 | Yes — use PDF/DOC | No |
| DB commit failure | 500 | No — retry | Yes (error) |
| File save failure | 500 | No — retry | Yes (error) |
| Unexpected exception | 500 | No | Yes (error, traceback) |

Flask's `@app.errorhandler(Exception)` catches unhandled exceptions, logs the traceback, and returns a generic 500 JSON response. This prevents stack traces from leaking to clients.

---

## File Upload Storage

Uploaded files are saved under `static/uploads/` using a UUID-based filename to prevent collisions and path traversal:
```
static/uploads/<uuid4>.<ext>
```
The original filename is stored in `LibraryFile.filename` for display only. The `file_path` column stores the UUID filename. `send_from_directory` uses `UPLOAD_FOLDER` (absolute path), never a user-supplied path.

On Render's free tier the filesystem is ephemeral (wiped on redeploy). This is acceptable for v1 and noted in the requirements' Out of Scope. The `UPLOAD_FOLDER` directory is created at startup if it doesn't exist.

---

## Seeding Super Admin (`seed.py`)

Called from `run.py` and from the Docker entrypoint before Gunicorn starts.

```python
def seed_super_admin():
    email = os.environ.get("SUPER_ADMIN_EMAIL", "admin@campusconnect.app")
    password = os.environ.get("SUPER_ADMIN_PASSWORD", "ChangeMe123!")
    if not User.query.filter_by(role="super_admin").first():
        user = User(name="Super Admin", email=email,
                    password_hash=generate_password_hash(password),
                    role="super_admin", active=True)
        db.session.add(user)
        db.session.commit()
```

The seed runs inside an `app.app_context()`. Environment variables `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD` are set in `render.yaml`. For local dev they fall back to the defaults above. The hardcoded defaults are acceptable for local dev only; production must override them.

---

## Frontend Architecture

### `templates/index.html`

A single HTML file containing:
- `<head>` with PWA meta tags, theme-color, viewport, link to `style.css`, and `manifest.json`.
- `<body>` with a `#app` div (content mount point) and a `#bottom-nav` bar.
- Script tags loading JS modules in order: `app.js` last, all others before it.

### `static/js/app.js` — Router & State

`app.js` owns:
- `state = { token, user, currentPage }` — in-memory, with `localStorage` persistence for `token` and `user`.
- `router(page, params)` — calls `clearContent()`, then the appropriate module's `render(params)` function.
- Bottom nav click handlers → `router(...)`.
- On load: if no token, render login; else fetch `/api/auth/me` to validate token, then render dashboard.
- `api(method, path, body, isFormData)` — shared fetch wrapper that injects `Authorization: Bearer <token>`, handles 401 (redirect to login), and throws on non-OK responses with the `message` field.

### Per-feature JS modules

Each module exports a single `render(params)` function that:
1. Sets `#app`'s innerHTML to a skeleton/loading state.
2. Calls the relevant API endpoint(s) via `api(...)`.
3. Populates `#app` with rendered HTML.
4. Attaches event listeners for forms, buttons, filters.

Modal pattern for create/edit forms: a `<div class="modal">` is appended to `body`, styled with CSS, and removed on cancel/submit.

Role-based UI: each module checks `state.user.role` before rendering admin controls. This is UI-only convenience; server RBAC is the authority.

### Bottom Navigation

```html
<nav id="bottom-nav">
  <button data-page="dashboard">🏠 Dashboard</button>
  <button data-page="timetable">📅 Timetable</button>
  <button data-page="library">📚 Library</button>
  <button data-page="community">💬 Community</button>
  <button data-page="more">⋯ More</button>
</nav>
```

"More" opens a drawer listing: Marketplace, Lost & Found, Announcements, Assignments, Admin (if applicable).

On desktop (> 768px), `bottom-nav` is hidden via CSS; a `#sidebar` replaces it (same links, vertical layout, shown via media query).

### CSS Architecture (`static/css/style.css`)

CSS custom properties define the palette:
```css
:root {
  --primary: #6C3CE1;
  --accent: #F5A623;
  --bg: #ffffff;
  --text: #1a1a2e;
  --danger: #e53e3e;
  --success: #38a169;
  --card-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

Layout: flex-column body with a `#app` flex-grow content area and fixed `#bottom-nav` at the bottom (mobile). Cards use `border-radius: 12px` and `var(--card-shadow)`. Overdue assignments use `color: var(--danger)`. Timetable colour dots use inline `background-color` from the slot's `color` field.

---

## PWA Implementation

### `static/manifest.json`
```json
{
  "name": "CampusConnect",
  "short_name": "CampusConnect",
  "description": "Kila Kitu Made Easy",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#6C3CE1",
  "icons": [
    { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```
Icon PNGs (192×192 and 512×512) are generated as simple purple squares with "CC" text as SVG-to-PNG data URIs embedded in the HTML, or as static PNG files committed to the repo.

### `static/sw.js` — Service Worker

Uses a Cache-First strategy for the app shell:
```javascript
const CACHE_NAME = "campusconnect-v1";
const SHELL_ASSETS = ["/", "/static/css/style.css", "/static/js/app.js",
  /* all other JS modules */, "/static/manifest.json"];

self.addEventListener("install", e => e.waitUntil(
  caches.open(CACHE_NAME).then(c => c.addAll(SHELL_ASSETS))
));

self.addEventListener("fetch", e => {
  if (e.request.url.includes("/api/")) return; // Network-only for API
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
```
API calls always go to the network. If the network is unavailable and the resource is not cached, the fetch rejects — `api()` in `app.js` catches this and shows "You are offline. Please check your connection."

The service worker is registered in `index.html`:
```html
<script>
  if ('serviceWorker' in navigator)
    navigator.serviceWorker.register('/static/sw.js');
</script>
```

---

## Deployment

### `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p static/uploads
ENV FLASK_ENV=production
EXPOSE 5000
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:5000 --workers 2 'app:create_app()'"]
```

The CMD runs the seed script first, then starts Gunicorn with 2 workers (safe for SQLite with single-writer semantics). `--timeout 120` is added to handle large file uploads.

### `render.yaml`
```yaml
services:
  - type: web
    name: campusconnect
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python seed.py && gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 'app:create_app()'
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: SUPER_ADMIN_EMAIL
        value: admin@campusconnect.app
      - key: SUPER_ADMIN_PASSWORD
        sync: false   # set manually in Render dashboard
      - key: DATABASE_URL
        value: sqlite:///campusconnect.db
```

Render's free tier uses the native Python environment (not Docker) for faster cold starts; the `Dockerfile` is for `docker build` / local container use. Both paths share the same `seed.py + gunicorn` start sequence.

### `requirements.txt`
```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-JWT-Extended==4.6.0
Flask-CORS==4.0.1
Werkzeug==3.0.3
gunicorn==21.2.0
python-dotenv==1.0.1
```

---

## Testability Notes

The app factory pattern (`create_app()`) enables test clients: `app = create_app(); client = app.test_client()`. Each Blueprint can be tested in isolation by registering only it. SQLite in-memory (`sqlite:///:memory:`) can replace the file DB in tests. The `seed_super_admin()` function is importable from `seed.py`. Upload paths can be redirected to a temp directory. These hooks exist even though an automated test suite is out of scope for v1.

---

## Edge Cases

1. **Concurrent likes**: Two users liking simultaneously may both read the same `likes` count. SQLite's serialised writes mean only one wins; the other's increment is lost. Acceptable for v1 (like counts are approximate).
2. **Timetable day boundary**: `today_classes` uses UTC day. Students in timezones significantly ahead of UTC may see the wrong day. For v1, UTC is used consistently and noted as a known limitation.
3. **Assignment due_date as date vs datetime**: `due_date` is stored as `date`; overdue check is `due_date < date.today()` (UTC). An assignment due "today" is not overdue until tomorrow.
4. **File naming collision**: UUID filenames make collision astronomically unlikely; no additional collision check is needed.
5. **Super admin institution_id = NULL**: All institution-scoped endpoints check `institution_id` from the JWT claims. If the caller is `super_admin` and `institution_id` is NULL, the endpoint returns 403 (super admin uses only `/api/admin/*` routes, never institution-scoped ones).
6. **Course deletion**: Deleting a course that has timetable slots, library files, or assignments leaves orphaned FK records. For v1, the admin UI warns about this but the cascade delete is not implemented — the DB `ON DELETE RESTRICT` (SQLAlchemy default) will return a 500 which is caught and surfaced as "Cannot delete: course has associated records."
7. **Large library on mobile**: Paginated lists (20 per page) keep initial payloads small. Download links stream directly from the server.
8. **SW cache invalidation**: Incrementing `CACHE_NAME` to `campusconnect-v2` on the next deploy triggers `activate` event cleanup of old caches.
