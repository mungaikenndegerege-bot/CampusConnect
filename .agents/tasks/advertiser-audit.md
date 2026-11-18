# CampusConnect Advertiser System — Audit Report

## Summary Answers

| Question | Answer |
|---|---|
| Ad model fields | `id`, `title`, `body`, `image_path`, `link_url`, `active`, `click_count`, `created_at` |
| click_count increment | Blind `+= 1` on `POST /api/ads/<id>/click`, no validation, no deduplication |
| Impressions tracked | **No.** Zero impression tracking exists anywhere in the codebase |
| Advertiser/campaign concept | **No.** Ads are flat admin-only records with no owner, no campaign, no schedule |
| Admin ad management | A single tab: create/toggle active/delete — no approval workflow, no analytics |
| Python charting libraries | **None.** `requirements.txt` contains only Flask, SQLAlchemy, CORS, Werkzeug, gunicorn, python-dotenv |

---

## Evidence by File

### `app/models.py` — Full Schema

**Existing `Ad` model** (`ad` table, lines 56–64):
```python
class Ad(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    body        = db.Column(db.Text, nullable=False)
    image_path  = db.Column(db.String(255))
    link_url    = db.Column(db.String(500))
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)
```

There is no `campaign_id`, no `advertiser_id`, no `start_date`, no `end_date`, no `impression_count`, no `placement` field. The model is a minimal content record, not an ad-tech entity.

**Other models present:**
- `Post`, `Comment` — community board posts and comments
- `MarketplaceItem` — classified listings with image upload
- `LostFoundItem` — lost/found reports
- `Announcement` — pinned admin notices
- `AdminSession` — single-admin token auth (hardcoded credentials)
- `Account` / `AccountSession` — public user registration with bcrypt passwords and 30-day bearer tokens
- `Report` — user content reports awaiting admin resolution
- `InstitutionCategory`, `Institution`, `InstitutionCommunity`, `InstitutionPost`, `InstitutionPostComment` — institution directory and community board

**Notable gaps:** No foreign-key link between `Account` and any ad or campaign. No models at all for advertisers, campaigns, placements, payments, impressions, clicks, conversions, or daily stats.

---

### `app/admin.py` — Admin Ad Routes

Five ad routes exist:

| Route | Method | What it does |
|---|---|---|
| `GET /api/admin/ads` | GET | List all ads, ordered by `created_at` desc |
| `POST /api/admin/ads` | POST | Create ad with title, body, link_url, image, active flag |
| `PUT /api/admin/ads/<id>` | PUT | Update title/body/link_url/active/image |
| `DELETE /api/admin/ads/<id>` | DELETE | Hard delete |
| *(none)* | — | No analytics, no approval, no campaign linkage |

Authentication is a single hardcoded credential pair (`Adminmungai` / `Mungai2300`) validated against `AdminSession` tokens that expire after 24 hours. All admin routes use `require_admin()` which checks the `X-Admin-Token` request header.

The `ad_to_dict` serialiser in `admin.py` returns: `id, title, body, image_path, link_url, active, click_count, created_at`.

---

### `app/public.py` — Ad Serving and Click Tracking

**`GET /api/ads/active`** (line ~110):
```python
@public_bp.route('/api/ads/active')
def get_active_ads():
    ads = Ad.query.filter_by(active=True).order_by(Ad.created_at.desc()).all()
    return jsonify([ad_to_dict(a) for a in ads])
```
Returns all active ads in full. No filtering by date, placement, institution, or campaign.

**`POST /api/ads/<id>/click`** (line ~116):
```python
@public_bp.route('/api/ads/<int:aid>/click', methods=['POST'])
def click_ad(aid):
    ad = Ad.query.get_or_404(aid)
    ad.click_count += 1
    db.session.commit()
    return jsonify({'ok': True})
```
Blind increment. No IP deduplication, no session deduplication, no bot detection, no timestamp recording, no campaign attribution, no placement context.

There is **no impression endpoint at all**.

---

### `app/__init__.py` — Registered Blueprints

```
public_bp          — /api/* public routes
admin_bp           — /api/admin/* admin routes
accounts_bp        — /api/accounts/* user auth routes
institutions_bp    — /api/institutions/* public institution routes
admin_inst_bp      — /api/admin/institutions/* admin institution routes
```

No advertiser blueprint. No analytics blueprint.

---

### `templates/admin.html` — Admin Panel Structure

A single-page admin shell. The `<nav class="admin-tabs">` has seven tabs:

```
Ads | Announcements | Posts | Marketplace | Lost & Found | Reports | Institutions
```

Tab content is rendered entirely by JavaScript into `<div id="admin-tab-content">`. The HTML itself is 40 lines. There are no chart elements, no stats cards, no campaign tables. The template loads only `/static/css/style.css` and `/static/js/admin.js`.

---

### `static/js/admin.js` — Ads Tab Implementation

`loadAdsTab()` renders a create form and a flat list of ad cards. Each card shows:
- Title, body preview (80 chars)
- Clicks count
- Active/inactive badge
- Activate/Deactivate toggle button
- Delete button

`createAd()` submits a FormData POST. `toggleAd()` PUTs `{active}`. `deleteAd()` sends DELETE with a `confirm()` dialog.

There are no chart calls, no date filters, no impression counts, no campaign-level grouping.

---

### `static/js/app.js` — Ad Injection into Feed

On `DOMContentLoaded`, the app fetches `/api/ads/active` and stores the result in `state.ads`. The `injectAds(items)` function inserts one ad after every 5th feed item, cycling through `state.ads` by index (round-robin).

`renderAdBanner(ad)` renders an HTML string with a "Sponsored" label, optional image, title, body, and "Learn More" link. The click tracking fires inline:

```javascript
onclick="fetch('/api/ads/${ad.id}/click',{method:'POST'})"
```

This fires on every click of the link element. There is no IntersectionObserver, no visibility threshold, no deduplication guard, and no impression event anywhere in `app.js`, `feed.js`, or any other frontend file.

---

### `static/js/feed.js` — Feed Rendering

`renderFeed()` calls `injectAds(items)` and dispatches to per-type render functions. When an item has `type === 'ad'`, it calls `renderAdBanner(item)` from `app.js`. `feed.js` itself has no ad-specific logic — it delegates completely to `app.js`.

---

### `requirements.txt` — Available Packages

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.1
Werkzeug==3.0.3
gunicorn==22.0.0
python-dotenv==1.0.1
```

No charting library (matplotlib, plotly, etc.), no PDF library (reportlab, weasyprint, etc.), no task queue (Celery, RQ), no caching layer (Redis), no JWT library, no email library. Everything needed for the advertiser system must be added to `requirements.txt`.

---

### `Dockerfile` / `render.yaml` — Deployment

The app runs on [Render](https://render.com) as a Python web service:

```
buildCommand: pip install -r requirements.txt && python seed.py
startCommand: gunicorn -w 2 -b 0.0.0.0:$PORT run:app
```

`seed.py` calls `db.create_all()` then runs institution seeding. Any new SQLAlchemy models will be picked up by `db.create_all()` on the next deploy without a migration tool — the app does not use Flask-Migrate. This is both a convenience (no migration files needed) and a constraint (no safe rollback for schema changes in production without manual intervention).

**Database:** SQLite at `sqlite:///campusconnect.db` (Render ephemeral filesystem — uploads and DB are reset on each deploy/restart unless a persistent disk is attached). This is a critical constraint: the production database is not durable. The advertiser system must either stay SQLite-compatible for the short term or the deployment must be upgraded to a persistent store (Render PostgreSQL or similar).

**Uploads:** Stored at `static/uploads/` (local filesystem, also ephemeral on Render without a disk mount).

---

## Conclusions

### What Does Not Exist At All (Must Be Created)

1. **Database tables:** `advertiser`, `advertiser_session`, `ad_campaign`, `advertisement` (extended), `ad_placement`, `ad_impression`, `ad_click`, `ad_conversion`, `ad_daily_stats`, `ad_payment`
2. **Advertiser auth system:** Registration, email verification, login, JWT or session tokens, password reset — completely absent
3. **Impression tracking:** No server endpoint, no frontend IntersectionObserver, no deduplication, no bot detection
4. **Campaign management:** No campaign concept, no start/end dates, no budget, no status workflow (draft → pending approval → active → paused → completed)
5. **Approval workflow:** Admin can toggle active/inactive but there is no pending/approved/rejected state for either advertisers or campaigns
6. **Advertiser dashboard:** No HTML template, no route, no JS, no charts
7. **Analytics API:** No aggregation queries, no daily stats, no CTR calculation, no reach/unique visitor concept
8. **Report download:** No PDF or CSV export
9. **Placement system:** Ads currently have no placement field; they all go into the same feed injection pool
10. **Payment tracking:** Nothing exists
11. **Python dependencies:** `reportlab` or `weasyprint` (PDF), `fpdf2` or similar (CSV via stdlib is fine), potentially `flask-mail` or similar for email notifications

### What Exists and Can Be Extended

| Existing Asset | Extension Needed |
|---|---|
| `Ad` model (8 fields) | Add `campaign_id FK`, `placement_id FK`, `impression_count` counter cache; keep existing fields |
| `POST /api/ads/<id>/click` | Replace blind increment with validated click event that writes to `ad_clicks` table |
| `GET /api/ads/active` | Extend to filter by placement, campaign date range; add impression-token response |
| `renderAdBanner()` in `app.js` | Add IntersectionObserver + deduplication + impression POST |
| `injectAds()` in `app.js` | Add placement context to ad selection |
| `loadAdsTab()` in `admin.js` | Extend with campaign management sub-tabs and analytics summary |
| `admin.html` tab nav | Add "Campaigns", "Advertisers", "Analytics", "Payments" tabs |
| `Account` / `AccountSession` models | The advertiser auth can follow the same pattern (separate `advertiser` table linked to its own sessions) |
| `app/__init__.py` | Register new `advertiser_bp` and `advertiser_admin_bp` blueprints |
| `seed.py` / `db.create_all()` | New models are picked up automatically — no migration tool needed |
| `config.py` | Add `ADVERTISER_SESSION_DAYS`, file size limits for campaign uploads, any new env vars |
| Rate limiting (`ratelimit.py`) | Reuse `check_rate_limit` decorator on impression/click endpoints |

### Recommended Additions to `requirements.txt`

```
Flask-Login or manual session pattern (already established — stick with manual)
reportlab==4.2.x          # PDF report generation
Pillow==10.x.x             # image processing/validation for ad uploads (already used implicitly via Werkzeug)
```

For CSV export, Python's built-in `csv` module is sufficient — no extra package needed.

### Critical Infrastructure Decision Required

**SQLite on Render is ephemeral.** Every deploy wipes the database. For a production advertiser system with real payments and analytics:

- **Option A (minimum viable):** Attach a Render persistent disk (`/data`) and point `SQLALCHEMY_DATABASE_URI` at `/data/campusconnect.db`. Zero code change, $7/month on Render. Still SQLite — works for small scale.
- **Option B (recommended for advertiser data):** Migrate to Render PostgreSQL (free tier available). Requires changing `SQLALCHEMY_DATABASE_URI` and adding `psycopg2-binary` to `requirements.txt`. All SQLAlchemy model definitions are already compatible.

This decision should be made before implementing the advertiser tables, because a data-loss event after advertiser payments are recorded would be a serious problem.

### Security Gaps to Address Alongside Implementation

- Admin credentials are hardcoded in `admin.py` as plaintext strings (`Adminmungai` / `Mungai2300`). This must be moved to environment variables before advertisers interact with the system.
- The click endpoint has no CSRF protection, no origin check, and no rate limit — trivial to inflate. This must be fixed before any advertiser pays for clicks.
- Uploaded files are served directly from `static/uploads/` with no access control — any URL is publicly accessible. Campaign creative assets should be fine here, but this is worth noting.

---

## Recommended Implementation Order

Mirroring the user's stated sequence:

1. **Database schema** — Define all new models in `app/models.py`; `db.create_all()` picks them up on next start
2. **Advertiser auth** — Register/login/session in new `app/advertiser.py` blueprint, following `accounts.py` pattern
3. **Campaign management** — CRUD for campaigns and advertisements, with approval states
4. **Impression tracking** — Server endpoint + frontend IntersectionObserver with dedup cookie/localStorage key
5. **Click tracking** — Replace blind increment with validated `ad_clicks` row insert
6. **Analytics aggregation** — Daily stats rollup queries, CTR calculation, reach via privacy-preserving identifiers
7. **Advertiser dashboard** — New `templates/advertiser.html` + `static/js/advertiser.js` + Chart.js (CDN or bundled)
8. **Admin extensions** — New tabs in `admin.html` for campaign approval, advertiser management, platform revenue
9. **Feed integration** — Update `renderAdBanner()` and `injectAds()` to use placement-aware campaign ads
10. **Report download** — PDF via reportlab, CSV via stdlib, triggered from advertiser dashboard
11. **Deployment hardening** — Persistent DB, env-var credentials, rate limits on tracking endpoints
