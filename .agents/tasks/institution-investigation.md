# CampusConnect — Institution Directory Investigation Report

**Date:** 2026  
**Purpose:** Pre-implementation analysis for the Kenyan educational institution directory and community grouping feature.

---

## Summary

CampusConnect is a lightweight Flask + SQLAlchemy SPA with SQLite. It has **10 existing database models**, **3 registered blueprints**, **28 API endpoints**, a single-page frontend driven by vanilla JS section-switching, and an admin dashboard. There are **no existing institution, community, or user-preference tables**. The entire schema must be added fresh. The app structure is clean and well-understood — adding the institution system requires new models, two new blueprints (public institution API + admin institution API), new JS files, and extending both HTML templates. No existing functionality needs breaking changes.

---

## 1. Database Models (`app/models.py`)

Ten SQLAlchemy models are defined. None relate to institutions, communities, or institution preferences.

### Existing tables

| Table | Key columns | Notes |
|---|---|---|
| `post` | id, poster_name, poster_contact, title, body, topic, created_at, deleted | No institution FK |
| `comment` | id, post_id (FK→post), poster_name, body, created_at | |
| `marketplace_item` | id, poster_name, poster_contact, title, description, price, category, image_path, created_at, sold, deleted | |
| `lost_found_item` | id, poster_name, poster_contact, item_type, title, description, location, created_at, resolved, deleted | |
| `announcement` | id, title, body, created_at, pinned | Global announcements only |
| `ad` | id, title, body, image_path, link_url, active, created_at, click_count | |
| `admin_session` | id, token (unique), created_at | 24h expiry enforced in code |
| `account` | id, name, email, password_hash, bio, created_at, active | Optional accounts |
| `account_session` | id, account_id (FK→account), token (unique), created_at | 30-day expiry |
| `report` | id, content_type, content_id, reason, reporter_ip, created_at, resolved | content_type ∈ {post, marketplace, lostandfound} |

### What is missing for the new feature

All tables in the user brief (§J) are absent:
- `institution` / `institution_category`
- `institution_community`
- `community_membership` / `followed_institution`
- `user_institution_preference`
- `institution_post` / `institution_announcement`

The existing `Post` and `Announcement` models have no `institution_id` column. Institution-scoped posts will need either a new `institution_post` table (clean separation) or an `institution_id` nullable FK added to `post` (re-use existing feed machinery). Given the brief asks for separate institution community feeds and a national feed, a dedicated `institution_post` table is the safer design.

---

## 2. Blueprints (`app/__init__.py`)

Three blueprints are registered:

```python
from app.public import public_bp      # → app.register_blueprint(public_bp)
from app.admin import admin_bp        # → app.register_blueprint(admin_bp)
from app.accounts import accounts_bp  # → app.register_blueprint(accounts_bp)
```

Two hardcoded routes exist directly on `app`:
- `GET /` → `render_template('index.html')`
- `GET /admin` → `render_template('admin.html')`

**Notable:** The `__pycache__` directory contains compiled bytecode for modules `announcements`, `assignments`, `auth`, `community`, `dashboard`, `library`, `lostandfound`, `marketplace`, `timetable` — none of which are imported in `__init__.py`. These are dead/removed blueprints from a prior version. They must not be accidentally re-imported.

**New blueprints needed:**
- `app/institutions.py` → `institutions_bp` (public institution directory API)
- `app/admin_institutions.py` → logic can be appended to existing `admin_bp` or as a separate blueprint registered alongside it

---

## 3. Public Routes (`app/public.py`)

Blueprint prefix: none (routes mount at `/`).

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/feed` | Mixed feed: last 20 posts + market + L&F + announcements, sorted desc, capped at 50 |
| GET | `/api/posts` | Paginated posts (10/page), `?page=` |
| POST | `/api/posts` | Create post — rate-limited 5/hour per IP |
| GET | `/api/posts/<pid>/comments` | List comments |
| POST | `/api/posts/<pid>/comments` | Add comment |
| GET | `/api/marketplace` | Paginated marketplace (10/page) |
| POST | `/api/marketplace` | Create listing — rate-limited 3/hour, accepts multipart |
| GET | `/api/lostandfound` | Paginated L&F (10/page) |
| POST | `/api/lostandfound` | Create L&F report — rate-limited 5/hour |
| PUT | `/api/posts/<pid>` | Edit post (name-match auth) |
| PUT | `/api/marketplace/<mid>` | Edit listing (name-match auth) |
| PUT | `/api/lostandfound/<lid>` | Edit L&F item (name-match auth) |
| GET | `/api/announcements` | All announcements, pinned first |
| GET | `/api/ads/active` | Active ads |
| POST | `/api/ads/<aid>/click` | Track ad click |
| GET | `/api/uploads/<filename>` | Serve uploaded files |
| POST | `/api/report` | Submit content report — rate-limited 10/hour |

**New public endpoints needed** (institution directory):
- `GET /api/institutions` — list/search with filters (category, county, query, sort)
- `GET /api/institutions/<id>` — single institution detail
- `GET /api/institutions/<id>/community/posts` — institution community feed
- `POST /api/institutions/<id>/community/posts` — post to institution community
- `GET /api/institutions/<id>/community/posts/<pid>/comments` — comments
- `POST /api/institutions/<id>/community/posts/<pid>/comments` — add comment
- `GET /api/institutions/categories` — list categories
- `GET /api/institutions/counties` — list counties for filter
- `GET /api/institutions/popular` — most-selected institutions
- `POST /api/institutions/<id>/select` — record visitor institution selection (session/cookie)
- `POST /api/institutions/<id>/follow` — follow institution (account token or anonymous via localStorage)
- `GET /api/national/feed` — national feed across all institutions

---

## 4. Admin Routes (`app/admin.py`)

Blueprint prefix: none. All routes require `X-Admin-Token` header (checked via `require_admin()`). Token validated against `admin_session` table, 24h lifetime. Credentials are hardcoded: username `Adminmungai`, password `Mungai2300` (plain text comparison — a security note, but out of scope here).

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/admin/login` | Issue admin token |
| POST | `/api/admin/logout` | Revoke token |
| GET | `/api/admin/ads` | List all ads |
| POST | `/api/admin/ads` | Create ad |
| PUT | `/api/admin/ads/<aid>` | Edit ad |
| DELETE | `/api/admin/ads/<aid>` | Hard-delete ad |
| POST | `/api/admin/announcements` | Create announcement |
| DELETE | `/api/admin/announcements/<aid>` | Delete announcement |
| DELETE | `/api/admin/posts/<pid>` | Soft-delete post |
| DELETE | `/api/admin/marketplace/<mid>` | Soft-delete listing |
| DELETE | `/api/admin/lostandfound/<lid>` | Soft-delete L&F item |
| GET | `/api/admin/reports` | List unresolved reports |
| POST | `/api/admin/reports/<rid>/resolve` | Resolve report |

**New admin endpoints needed:**
- `GET /api/admin/institutions` — list all institutions
- `POST /api/admin/institutions` — create institution (auto-creates community)
- `PUT /api/admin/institutions/<id>` — edit institution
- `PATCH /api/admin/institutions/<id>/status` — activate/deactivate
- `DELETE /api/admin/institutions/<id>` — soft-delete (preserve community content)
- `POST /api/admin/institutions/import` — bulk CSV import
- `GET /api/admin/institutions/<id>/community` — view community info
- `POST /api/admin/institutions/<id>/community/announcements` — institution announcement

---

## 5. Frontend Structure

### Templates (at `templates/`, not `app/templates/`)
- `templates/index.html` — the SPA shell
- `templates/admin.html` — the admin dashboard shell

Both are minimal HTML shells that load CSS and JS; all rendering is done in JS.

### Static JS (`static/js/`)
| File | Purpose |
|---|---|
| `app.js` | State, `api()` helper, `navigate()`, modal, toast, ad injection |
| `feed.js` | `renderFeed()`, `openDetailModal()`, card render helpers |
| `community.js` | `renderCommunity()`, post/comment forms |
| `marketplace.js` | `renderMarketplace()`, item listing |
| `lostandfound.js` | `renderLostFound()`, L&F forms |
| `announcements.js` | `renderAnnouncements()` |
| `account.js` | Optional sign-in/register, `renderAccountBar()`, `openReportModal()` |
| `admin.js` | Entire admin dashboard logic |

### Other static files
- `static/css/style.css` — single stylesheet (blue-and-white design)
- `static/manifest.json` — PWA manifest
- `static/sw.js` — service worker
- `static/icons/` — 192px and 512px PWA icons
- `static/uploads/` — user-uploaded images

---

## 6. Navigation and Section System (`app.js` + `feed.js`)

### Section routing (app.js)

The SPA uses a simple `state.section` string. Navigation is driven by `navigate(section)`:

```javascript
const state = { section: 'feed', ads: [], adIndex: 0 };

function navigate(section) {
  state.section = section;
  // highlights matching bottom-nav button
  // shows/hides FAB based on section
  const renders = { feed: renderFeed, community: renderCommunity, 
                    marketplace: renderMarketplace, lostandfound: renderLostFound, 
                    announcements: renderAnnouncements };
  renders[section]();
}
```

Bottom nav in `index.html` has five buttons: `feed`, `community`, `marketplace`, `lostandfound`, `announcements`. Each calls `navigate(b.dataset.section)` on click.

**To add an institutions section:** add a 6th `<button data-section="institutions">` to `#bottom-nav` in `index.html`, add `institutions: renderInstitutions` to the `renders` map in `navigate()`, and create `static/js/institutions.js`.

### FAB (floating action button)

The FAB is shown only for `community`, `marketplace`, `lostandfound`. Institution posting can follow the same pattern — add `institutions: '+ Post'` to `fabLabels`.

### Modal system

`openModal(html)` / `closeModal()` drive all dialogs. The institution picker and community post forms should use the same modal system.

### Ad injection

`injectAds(items)` inserts one ad every 5 items. Institution feeds can call the same function.

### Account bar (`account.js`)

`renderAccountBar()` runs on `DOMContentLoaded`. It reads `localStorage` keys `cc_account_token` / `cc_account_data`. Institution preferences can be stored alongside these using `cc_institution_pref` and `cc_followed_institutions` keys for anonymous visitors, with server-side persistence when an account exists.

---

## 7. Dockerfile and Requirements

### `requirements.txt`
```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.1
Werkzeug==3.0.3
gunicorn==22.0.0
python-dotenv==1.0.1
```

**No CSV parsing library is listed.** Python's built-in `csv` module handles CSV import without an additional package. No migration library (Alembic/Flask-Migrate) is present.

### `Dockerfile`
```
FROM python:3.11-slim
RUN pip install -r requirements.txt
RUN python seed.py      ← runs db.create_all() at build time
EXPOSE 5000
CMD gunicorn -w 2 -b 0.0.0.0:5000 run:app
```

**Key implication:** `seed.py` calls `db.create_all()`. This is the **only migration mechanism**. Any new tables added to `models.py` will be created automatically on the next Docker build or server restart. There is no need to add Flask-Migrate for this project — but `db.create_all()` will not modify existing tables if columns are added to them. For this feature we are adding entirely new tables, so `db.create_all()` is sufficient.

### `config.py`
- Database: SQLite at `instance/campusconnect.db`
- Upload folder: `static/uploads/`
- Max upload: 5 MB
- Allowed image extensions: jpg, jpeg, png, webp
- Secret key from env var `SECRET_KEY`, defaults to a dev value

The database URI is a relative SQLite path. This is fine for single-instance deployment on Render (confirmed by `render.yaml`).

---

## 8. Conclusions and Recommendations

### What is clean and well-suited for extension
- Blueprint pattern is consistent; adding new blueprints is straightforward.
- `db.create_all()` as migration is fine for net-new tables only.
- The JS `navigate()` + render function pattern scales directly — a new section is one nav button + one render function + one JS file.
- The modal system works for institution picker UI.
- `localStorage` already stores account token/data; institution preferences follow the same pattern for anonymous users.

### Key design decisions the implementation must make

1. **Institution posts vs. re-using `Post` table.**  
   Add a new `InstitutionPost` model (mirrors `Post` but with `institution_id` FK). This avoids adding a nullable column to the existing `post` table and keeps the national feed and institution feeds cleanly separated. The existing `Post` model and its API become the "national/general" feed.

2. **Community auto-creation trigger.**  
   On `POST /api/admin/institutions`, the handler must immediately `INSERT` a row into `institution_community` with `institution_id` set. No separate step.

3. **Anonymous institution preference storage.**  
   For visitors without accounts, store selected institution ID in `localStorage` under key `cc_institution_id`. On account creation/login, the frontend should POST this to the server to persist it. The `Account` model needs an `institution_id` nullable FK column added.

4. **No new Python packages needed.**  
   CSV import uses `import csv` (stdlib). The existing stack handles everything else.

5. **Admin dashboard extension.**  
   Add an `institutions` tab to `admin.html`'s `<nav class="admin-tabs">` block and add the corresponding `loadInstitutionsTab()` function in `admin.js`. Institution admin API routes can be added to the existing `admin_bp` in `admin.py` (or a new `admin_institutions_bp` registered in `__init__.py` — either works; a single file is simpler given the project's style).

6. **No `institution_post` for marketplace/L&F.**  
   The brief does not mention institution-scoped marketplace or L&F, so those remain global.

7. **`account` table migration concern.**  
   Adding `institution_id` to the existing `account` table will NOT be applied by `db.create_all()` on an already-running instance. The implementation must either: (a) make it a new table `user_institution_preference` keyed on `account_id` (safe, no alter needed), or (b) instruct the operator to delete and recreate the SQLite file on first deploy. Option (a) is safer and matches the brief's §J table list (`user_institution_preferences` is called out as a separate table).

### Files to create (new)
- `app/institutions.py` — public institution API blueprint
- `static/js/institutions.js` — institution picker + community UI
- Optionally: `static/js/institution-admin.js` (or extend `admin.js`)
- Institution seed data file: `data/institutions.py` or inline in `seed.py` extension

### Files to modify (existing)
- `app/models.py` — add ~8 new models
- `app/__init__.py` — register new blueprint(s)
- `app/admin.py` — add institution admin routes (or separate file)
- `templates/index.html` — add institutions nav button, load `institutions.js`
- `templates/admin.html` — add institutions admin tab
- `static/js/app.js` — add `institutions: renderInstitutions` to `navigate()`'s renders map
- `static/js/admin.js` — add `loadInstitutionsTab()` and related functions
- `static/css/style.css` — institution card styles, picker modal styles
- `seed.py` — extend to seed institution data after `db.create_all()`

### No breaking changes required
All existing routes, models, and JS remain intact. The institution system layers on top. Existing `Post` data and the global feed are unaffected.
