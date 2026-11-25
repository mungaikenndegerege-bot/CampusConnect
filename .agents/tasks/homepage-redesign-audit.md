# CampusConnect – Homepage Redesign & Platform Enhancement Audit

**Date:** 2026-11-28  
**Scope:** Full codebase audit of `c:\Users\user\Documents\NetBeansProjects\CampusConnect`  
**Purpose:** Drives the homepage redesign and platform enhancement task

---

## Executive Summary

CampusConnect is a working, multi-feature Flask SPA. The backend is well-structured with 13 Python source files, a 24-table SQLite/PostgreSQL database, Supabase-compatible storage, and 10 API blueprints. The frontend is a single-page app (SPA) driven by vanilla JavaScript loaded into `templates/index.html`. The platform already has a solid foundation — community posts, marketplace, lost & found, announcements, institution directory with per-institution communities, events, jobs/internships, reactions, notifications, and a full advertiser portal.

**What's already working:**
- Student feed aggregating posts, marketplace, lost & found, announcements
- Community posts with comments, file/image attachments, topic filtering
- Marketplace with categories, images, owner-token edit/delete
- Lost & found
- Announcements (admin-only posting, correctly enforced)
- Institutions directory (600+ Kenyan institutions seeded) with per-institution community posts and comments
- Events (create, edit, delete with owner token; poster image upload)
- Jobs & internships (`Opportunity` model, `campus.py` routes)
- Reactions (like/celebrate/support) on posts, institution posts, events, opportunities
- Notifications model and API (read, mark-read)
- Account system (register, login, logout, profile update with bio and institution link)
- Advertiser portal (register → admin approval → campaigns → placements → impressions/clicks/stats)
- Admin panel (ads, announcements, posts, marketplace, lost & found, reports, institutions, advertiser management, campaign approval, revenue, payments)
- Content reporting system
- Rate limiting, idempotency protection, file signature validation, owner-token-based content editing
- PWA manifest and service worker

**What's missing or incomplete:**
- No homepage dashboard (currently just navigates to Feed on load)
- Groups section: nav button exists, no render function and no backend
- Accommodation section: nav button exists, no render function and no backend
- Scholarships: not in `Opportunity.opportunity_type` (only `job` and `internship` allowed)
- Private messaging: model, routes, and UI absent
- User profile page: Account model exists but no profile view beyond the account bar
- Password reset / email verification: not implemented
- Google sign-in: not implemented
- Global search: search bar in header exists, not wired to any handler
- Roommate finder: no model, routes, or UI
- Nearby services: no model, routes, or UI
- Learning hub / file sharing: file upload works in community posts but no dedicated section
- Business profiles: Advertiser model exists but no public-facing profile pages
- Trending posts algorithm: feed is chronological, no score/weight
- Dynamic homepage dashboard with real data sections: not implemented
- `account.js` has `showMyPosts()` returning "coming soon"
- Two nav items ("Groups", "Rooms") navigate to undefined `renderGroups()`/`renderAccommodation()` — these will silently fail or throw a JS error

**Three deleted/stale modules** have `.pyc` files but no source: `announcements.py`, `auth.py`, `community.py`, `marketplace.py`, `library.py`, `timetable.py`, `assignments.py`, `dashboard.py`, `lostandfound.py`. Their logic has been consolidated into `public.py` and `campus.py`. This is not a problem but confirms previous refactors.

---

## 1. Python Files — `app/`

| File | Purpose | Key Routes |
|------|---------|-----------|
| `__init__.py` | App factory; registers all blueprints | `GET /`, `GET /health`, `GET /api/uploads/<path>`, `GET /admin`, `GET /advertiser` |
| `models.py` | All 24 ORM models | (see §2) |
| `public.py` | Core public SPA routes — posts, marketplace, lost & found, announcements, ads | `GET/POST /api/feed`, `GET/POST/PUT/DELETE /api/posts`, `GET/POST /api/posts/<id>/comments`, `GET/POST/PUT/DELETE /api/marketplace`, `GET/POST/PUT/DELETE /api/lostandfound`, `POST/GET /api/announcements`, `GET /api/ads/active`, `POST /api/ads/<id>/click`, `POST /api/report` |
| `accounts.py` | User account auth — register/login/logout/profile | `POST /api/accounts/register`, `POST /api/accounts/login`, `GET/PUT /api/accounts/me`, `POST /api/accounts/logout` |
| `admin.py` | Admin dashboard API — ads, announcements, content moderation, users, advertiser management, campaign/payment management | `POST /api/admin/login`, `POST /api/admin/logout`, `GET/POST/PUT/DELETE /api/admin/ads`, `GET/POST/DELETE /api/admin/announcements`, `DELETE /api/admin/posts/<id>`, `DELETE /api/admin/marketplace/<id>`, `DELETE /api/admin/lostandfound/<id>`, `GET /api/admin/reports`, `POST /api/admin/reports/<id>/resolve`, `GET /api/admin/stats`, `GET/status /api/admin/accounts`, `GET/approve/reject /api/admin/advertisers`, `GET/approve/reject/pause/activate /api/admin/campaigns`, `GET/POST/PUT /api/admin/placements`, `GET /api/admin/revenue`, `GET/confirm /api/admin/payments` |
| `campus.py` | Events and opportunities (jobs/internships), reactions, notifications | `GET/POST /api/events`, `PUT/DELETE /api/events/<id>`, `GET/POST /api/opportunities`, `PUT/DELETE /api/opportunities/<id>`, `POST /api/reactions`, `DELETE /api/reactions/<type>/<id>`, `GET /api/notifications`, `PUT /api/notifications/<id>/read` |
| `institutions.py` | Institution directory CRUD, per-institution communities and posts | `GET /api/institutions`, `GET /api/institutions/categories`, `GET /api/institutions/counties`, `GET /api/institutions/popular`, `GET /api/institutions/<id>`, `GET/POST /api/institutions/<id>/posts`, `POST /api/institutions/<id>/join`, `GET/POST /api/institutions/<id>/posts/<pid>/comments`, `PUT /api/institutions/<id>/posts/<pid>` and admin variants at `/api/institutions/admin-*` and `/api/admin/institutions` |
| `advertiser.py` | Advertiser portal — register, login, campaigns, stats, CSV report | `POST /api/advertiser/register`, `POST /api/advertiser/login`, `POST /api/advertiser/logout`, `GET/PUT /api/advertiser/me`, `GET /api/advertiser/placements`, `POST/GET /api/advertiser/campaigns`, `GET /api/advertiser/campaigns/<id>`, `GET /api/advertiser/campaigns/<id>/stats`, `GET /api/advertiser/campaigns/<id>/report` |
| `ad_tracking.py` | Impression and click tracking with bot detection, deduplication, rate limiting | `POST /api/track/impression`, `POST /api/track/click/<ad_id>` |
| `content_security.py` | Utility functions: owner token issuance/verification, idempotency key hashing, required/optional text validators | (no routes) |
| `ratelimit.py` | In-memory per-IP rate limit decorator | (decorator) |
| `storage.py` | File upload abstraction supporting local disk and Supabase Storage | (no routes — called from other modules) |
| `institutions_seed.py` | One-time seed script for Kenyan institution data | (no routes) |

---

## 2. Database Schema — `app/models.py`

### Core content models

**`Post`** (`post`)
- `id`, `poster_name` (100), `poster_contact` (100), `title` (200), `body` (Text)
- `topic` (50, default `General`)
- `created_at`, `updated_at`
- `deleted` (bool)
- `file_path` (300), `file_type` (20) — image or file attachment
- `owner_token_hash` (64)
- Relationship: `comments` → `Comment`
- Index: `(deleted, created_at)`

**`Comment`** (`comment`)
- `id`, `post_id` → `post.id`, `poster_name` (100), `body` (Text)
- `parent_id` → `comment.id` (threaded replies, cascade delete)
- `created_at`, `updated_at`
- Index: `(post_id, created_at)`

**`MarketplaceItem`** (`marketplace_item`)
- `id`, `poster_name` (100), `poster_contact` (100), `title` (200), `description` (Text)
- `price` (50), `category` (50), `image_path` (255)
- `created_at`, `sold` (bool), `deleted` (bool)
- `owner_token_hash` (64)
- Index: `(deleted, sold, created_at)`

**`LostFoundItem`** (`lost_found_item`)
- `id`, `poster_name`, `poster_contact`, `item_type` (10: lost/found)
- `title`, `description` (Text), `location` (200)
- `created_at`, `resolved` (bool), `deleted` (bool)
- `owner_token_hash`
- Index: `(deleted, resolved, created_at)`

**`Announcement`** (`announcement`)
- `id`, `title`, `body` (Text)
- `created_at`, `pinned` (bool)
- Index: `(pinned, created_at)`

**`Ad`** (`ad`) — legacy admin-created ads
- `id`, `title`, `body`, `image_path`, `link_url`
- `active` (bool), `created_at`, `click_count` (int)

### Account system

**`Account`** (`account`)
- `id`, `name` (100), `email` (200, unique), `password_hash` (256)
- `bio` (Text), `created_at`, `active` (bool)
- `institution_id` → `institutions.id`
- Relationships: `institution` → `Institution`, `sessions` → `AccountSession`

**`AccountSession`** (`account_session`)
- `id`, `account_id` → `account.id`, `token` (64, unique index), `created_at`

**`AdminSession`** (`admin_session`)
- `id`, `token` (64, unique), `created_at`

**`Report`** (`report`)
- `id`, `content_type` (20: post/marketplace/lostandfound), `content_id` (int)
- `reason` (200), `reporter_ip` (50), `created_at`, `resolved` (bool)

### Institution directory

**`InstitutionCategory`** (`institution_categories`)
- `id`, `name` (100, unique)

**`Institution`** (`institutions`)
- `id`, `name` (200), `abbreviation` (20), `category_id` → `institution_categories.id`
- `ownership` (10: Public/Private), `county` (100), `town` (100)
- `website` (200), `source` (100), `active` (bool), `created_at`
- Relationship: `category`, `community` (one-to-one)
- Index: `(active, name)`

**`InstitutionCommunity`** (`institution_communities`)
- `id`, `institution_id` → `institutions.id` (unique)
- `member_count` (int), `post_count` (int), `created_at`

**`InstitutionPost`** (`institution_posts`)
- `id`, `institution_id` → `institutions.id`, `community_id` → `institution_communities.id`
- `poster_name` (100), `poster_contact` (100), `title` (200), `body` (Text)
- `topic` (50), `deleted` (bool)
- `file_path` (300), `file_type` (20)
- `owner_token_hash` (64), `created_at`

> **Bug:** `models.py` line ~148 has an orphaned `poster_name = db.Column(...)` statement outside any class definition inside `InstitutionPost.to_dict()`. This is a syntax artefact that may cause import errors in strict environments. It needs to be removed.

**`InstitutionPostComment`** (`institution_post_comments`)
- `id`, `post_id` → `institution_posts.id`
- `body` (Text), `created_at`

> **Note:** `InstitutionPostComment` lacks a `poster_name` column in the model definition, but the `to_dict()` method references `self.poster_name`. The `add_inst_post_comment` route in `institutions.py` does save `poster_name`, which means the column is likely present in the actual DB from migration but missing in the model definition as written. This is a discrepancy that should be fixed.

### Advertiser system

**`Advertiser`** (`advertisers`)
- `id`, `business_name` (200), `contact_name` (100), `email` (200, unique)
- `phone` (30), `password_hash` (256), `website` (200), `description` (Text)
- `status` (20: pending/approved/rejected), `approved_at`, `created_at`

**`AdvertiserSession`** (`advertiser_sessions`)
- `id`, `advertiser_id` → `advertisers.id`, `token` (64, unique index), `created_at`

**`AdPlacement`** (`ad_placements`)
- `id`, `name` (100), `description` (Text), `price_per_day` (float), `active` (bool)

**`AdCampaign`** (`ad_campaigns`)
- `id`, `advertiser_id` → `advertisers.id`, `name` (200)
- `start_date`, `end_date` (Date), `status` (20: pending/approved/rejected/paused/active)
- `total_budget` (float), `payment_status` (20: unpaid/paid), `created_at`

> **Bug:** `AdCampaign` definition in `models.py` is missing a closing `)` on `advertiser_id = db.Column(db.Integer, db.ForeignKey('advertisers.id')`. This is a syntax error that would prevent the app from starting. It has a `.pyc` so either the file on disk has a different version or Python 3.15 is lenient. The source file as read has this defect.

**`Advertisement`** (`advertisements`)
- `id`, `campaign_id` → `ad_campaigns.id`, `placement_id` → `ad_placements.id`
- `title` (200), `body` (Text), `image_path` (300), `link_url` (500)
- `status` (20: pending/approved/rejected/active), `created_at`

**`AdImpression`** (`ad_impressions`)
- `id`, `advertisement_id`, `campaign_id`, `visitor_hash` (64), `placement` (100), `recorded_at`
- Index: `(advertisement_id, recorded_at)`

**`AdClick`** (`ad_clicks`)
- `id`, `advertisement_id`, `campaign_id`, `visitor_hash`, `placement`, `destination_url`, `recorded_at`

**`AdDailyStat`** (`ad_daily_stats`)
- `id`, `advertisement_id`, `campaign_id`, `date`
- `impressions`, `unique_reach`, `clicks` (all int)
- Unique constraint: `(advertisement_id, date)`
- Index: `(campaign_id, date)`

**`AdPayment`** (`ad_payments`)
- `id`, `campaign_id`, `amount` (float), `payment_method` (50), `reference` (100)
- `status` (20: pending/confirmed), `created_at`, `confirmed_at`

### Campus / engagement models

**`Event`** (`events`)
- `id`, `title` (200), `description` (Text), `institution_id` → `institutions.id`
- `venue` (200), `starts_at`, `ends_at` (DateTime)
- `poster_name` (100), `contact` (100), `poster_path` (300)
- `active` (bool), `created_at`, `updated_at`, `owner_token_hash` (64)
- Index: `(active, starts_at)`

**`Opportunity`** (`opportunities`)
- `id`, `opportunity_type` (20: **only `job` or `internship`** — no scholarship/attachment in validation)
- `title` (200), `organization` (200), `description` (Text)
- `location` (200), `application_url` (500), `institution_id`, `closes_at`
- `poster_name` (100), `active` (bool), `created_at`, `updated_at`, `owner_token_hash`
- Index: `(active, created_at)`

**`Reaction`** (`reactions`)
- `id`, `account_id` → `account.id`, `target_type` (30), `target_id` (int)
- `reaction_type` (20: like/celebrate/support), `created_at`
- Unique: `(account_id, target_type, target_id)`
- Check: `target_type IN ('post', 'institution_post', 'event', 'opportunity')`

**`Notification`** (`notifications`)
- `id`, `account_id` → `account.id`, `title` (200), `body` (1000)
- `target_url` (500), `read_at`, `created_at`

**`IdempotencyRecord`** (`idempotency_records`)
- `id`, `resource_type` (40), `key_hash` (64), `resource_id` (int), `created_at`
- Unique: `(resource_type, key_hash)`

---

## 3. `templates/index.html`

Single HTML file serving the entire SPA. Structure:

**Head:** `style.css`, PWA manifest, theme-color `#6C3CE1`, small inline styles for account-bar buttons and `#top-bar` flex layout.

**Body:**
- `#app-shell` wrapper
  - `#top-bar` header: logo area (`CampusConnect` h1 + tagline), `#global-search` input (search bar — **not wired to any handler**), `#account-bar` div (populated by `account.js`)
  - `#adsense-slot` bar: static "Advertise Here" placeholder (not AdSense, just contact info)
  - `#main-content`: spinner placeholder, replaced by section renders
  - `#bottom-nav`: 10 buttons — `feed`, `community`, `marketplace`, `lostandfound`, `announcements`, `institutions`, `events`, `opportunities`, `groups`, `accommodation`
  - `#fab-container`: floating action button (hidden until a section with posting is active)
  - `#modal-overlay` / `#modal-box` / `#modal-close`: single shared modal
  - `#toast-container`: toast notification area
- `<footer>`: copyright, developer credit

**Scripts loaded** (in order):
1. `app.js` — state, API helper, navigation router, modal, toast, ad injection
2. `feed.js` — feed render, detail modal
3. `community.js` — community posts, comments, forms
4. `marketplace.js` — marketplace listings
5. `lostandfound.js` — lost & found
6. `announcements.js` — announcements
7. `account.js` — sign in/register modal, report modal
8. `institutions.js` — institution directory and per-institution communities
9. `campus.js` — events and opportunities

**Missing:** No script for the `groups` or `accommodation` nav sections. Clicking those nav buttons calls `navigate('groups')` and `navigate('accommodation')`, which looks up `renders['groups']` and `renders['accommodation']` in `app.js` — both are `undefined`. The call `renders[section]()` will throw `TypeError: undefined is not a function`. This is an active JS bug for those two nav items.

---

## 4. `static/css/style.css`

**CSS variables (`:root`):**
- Two `:root` blocks (original + visual refresh override):
  - `--primary: #5b21b6` (deep purple, overrides initial `#6C3CE1`)
  - `--primary-dark: #4c1d95`
  - `--navy: #0f172a`
  - `--accent: #7c3aed`
  - `--bg: #f6f7fb`
  - `--border: #e4e7ec`
  - `--text: #172033`
  - `--text-muted: #64748b`
  - `--shadow: 0 8px 24px rgba(15,23,42,.07)`
  - `--radius: 12px`, `--card-bg: #fff`

**Layout approach:** Mobile-first, fixed bottom nav, `#main-content` max-width 680–760px centered. At ≥900px: bottom nav transforms to a 210px fixed left sidebar; main content gets `margin-left: 210px`. Footer also gets the same margin at desktop.

**Key classes:**
- `.card` — white card with 16px radius, shadow
- `.ad-banner` — yellow-tinted sponsored card
- `.announcement-card` — purple gradient card
- `.inst-card` / `.inst-category-tabs` / `.inst-abbr-badge` — institution directory UI
- `.spinner` — CSS animated loading indicator
- `.empty-state` — centered placeholder with icon
- `.badge` / `.badge-accent` / `.badge-green` / `.badge-red` — small colored pill labels
- `.btn-primary` — full-width purple gradient button
- `.load-more-btn` — bordered load-more button
- `.form-group` / `.form-input` — form layout
- `.toast` — floating notification

**Current gaps:** No dark mode, no skeleton loading states, no dashboard-specific grid classes, no accommodation/groups section styling.

---

## 5. `static/js/app.js` — State, Navigation, API

**State:** `{ section: 'feed', ads: [], adIndex: 0 }`

**`api(method, path, body, isFormData, extraHeaders)`:** Fetch wrapper. Automatically injects `X-Admin-Token` from `localStorage` into every request. Does NOT inject `X-Account-Token` — that's done separately in `account.js` via `accountApi()`. This creates inconsistency: authenticated reactions/notifications require `X-Account-Token` but `api()` won't send it.

**Navigation router:**
```js
const renders = {
  feed: renderFeed,
  community: renderCommunity,
  marketplace: renderMarketplace,
  lostandfound: renderLostFound,
  announcements: renderAnnouncements,
  institutions: renderInstitutions,
  events: renderEvents,
  opportunities: renderOpportunities
  // 'groups' and 'accommodation' are MISSING
};
```
Missing entries cause `TypeError` when those nav buttons are clicked.

**FAB labels:** `community`, `marketplace`, `lostandfound`, `events`, `opportunities` get a FAB button. `feed` and others do not.

**Ad injection:** Every 5th item in a list gets an ad banner from `state.ads`.

**`global-search`:** The input element exists in the DOM but has no event listener wired in `app.js` or any other JS file.

**DOMContentLoaded:** Loads active ads, sets up nav buttons and modal close, then calls `navigate('feed')`.

---

## 6. `static/js/feed.js`

**`renderFeed()`:** Calls `GET /api/feed` which returns up to 50 mixed items (posts, marketplace, lost & found, announcements sorted by `created_at`). Injects ads every 5 items. Shows institution quick-access button at top. Renders each item by type using `renderPostCard`, `renderMarketCard`, `renderLFCard`, `renderAnnCard`. Makes all cards clickable (opens detail modal).

**`openDetailModal(id, section)`:** Opens the shared modal with full detail view for community posts (with comment thread), marketplace items, lost & found, and announcements. For community posts: fetches the full post list again (fetches page 1 of `/api/posts`) to find the post by ID — this is inefficient; there is no `GET /api/posts/<id>` route.

**Missing:** Events and Opportunities are not rendered in the feed (they come from `/api/events` and `/api/opportunities`, not `/api/feed`). The feed is only community + marketplace + lostandfound + announcements.

---

## 7. `static/js/community.js`

**`renderCommunity()`:** Loads paginated posts from `GET /api/posts`. Renders with comments toggle, edit button, and report button.

**`toggleComments(btn)`:** Lazy-loads comments on click via `GET /api/posts/<id>/comments`. Renders comment thread and inline add-comment form.

**`openCommunityForm()`:** Modal form with name, contact, topic (General/Academic/Study Groups/Q&A), title, body, file attachment. File types: jpg/jpeg/png/webp/gif (image) or pdf/doc/docx (file).

**`submitCommunityPost()`:** Sends as FormData if file attached. Uses idempotency header. Saves owner token to localStorage.

**`editPost(pid)`:** Retrieves owner token from localStorage or prompts user. Opens edit form for title/body/topic. No delete button — only edit.

**Gap:** No delete button exposed to users (delete is owner-token-protected but no UI for it).

---

## 8. `static/js/marketplace.js`

**`renderMarketplace()`:** Paginated `GET /api/marketplace` with ad injection.

**`renderMarketItem(m)`:** Shows image, title, description, price in KSh format, category badge, contact row, edit button.

**`openMarketplaceForm()`:** Categories: Books, Electronics, Accessories, Accommodation, Other. Image upload optional.

**`editMarketItem(mid)`:** Edit title/description/price/category — no image re-upload on edit.

**Gap:** No "Mark as Sold" button in the user UI (backend supports it via admin delete, but no user-facing `sold` toggle). No search/filter UI in the marketplace section itself (backend supports `?q=` and `?category=`).

---

## 9. `static/js/campus.js`

**`renderEvents()`:** Lists all active events, shows poster image, title, description, date/venue badges, organizer. Owner-token holders get a "Remove my event" button.

**`openEventForm()`/`submitEvent()`:** Create events with poster upload. Idempotency protected.

**`renderOpportunities()`/`openOpportunityForm()`/`submitOpportunity()`:** Lists jobs and internships. Create form has type selector (internship/job). No filter UI.

**Gap:** No `opportunity_type === 'scholarship'` or `'attachment'` support — the backend validation in `campus.py` explicitly rejects anything not `job` or `internship`.

---

## 10. `static/js/institutions.js`

Full institution directory with:
- Search input, category tabs (All/Universities/Polytechnics/TTIs/TVETs/Specialised/Other), county dropdown
- Paginated card grid (`loadInstitutionCards`)
- Per-institution community view: posts, about tab
- "Select as My Institution" persists to `localStorage.cc_my_institution` and bumps member count via `POST /api/institutions/<id>/join`
- Institution badge in top bar showing current institution
- File attachments in institution posts

**Gap:** Institution community posts have no search or topic filter UI.

---

## 11. Other JS Files

| File | Purpose |
|------|---------|
| `static/js/account.js` | Sign in/register modal, `renderAccountBar()` (name + My Posts/Sign Out), `showMyPosts()` → stub "coming soon", `openReportModal()`/`submitReport()`, report modal |
| `static/js/announcements.js` | Simple read-only render of announcements from `GET /api/announcements`. No posting UI (correctly shows admin-only note) |
| `static/js/admin.js` | Full admin SPA for `templates/admin.html`. Tabs: ads, announcements, posts, marketplace, lostandfound, reports, institutions, advertisers, adcampaigns, placements, revenue, payments. Each tab has list + actions. Admin stats panel not visible in tabs but `GET /api/admin/stats` exists. |
| `static/js/advertiser.js` | Full advertiser portal SPA for `templates/advertiser.html`. Screens: login/register → dashboard → campaigns → new-campaign → campaign-detail → settings. Includes impression/click charts. |
| `static/js/lostandfound.js` | Paginated lost & found list, create/edit forms |

---

## 12. `requirements.txt`

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.1.0
Flask-CORS==4.0.1
Werkzeug==3.0.3
gunicorn==22.0.0
python-dotenv==1.0.1
psycopg[binary]==3.3.9
```

**Notable gaps for the enhancement task:**
- No email library (would need `Flask-Mail` or `sendgrid` for password reset / email verification)
- No OAuth library (would need `authlib` or `flask-dance` for Google sign-in)
- No full-text search (would need Postgres `tsvector` or a client-side approach)
- No WebSocket (would need `flask-socketio` for real-time private messaging / notifications)
- No geocoding (would need `geopy` or Google Maps API for nearby services)
- No image processing (would need `Pillow` for thumbnails)

---

## 13. What is Missing from the Requested Spec

### Already exists and works

| Feature | Status | Evidence |
|---------|--------|---------|
| Student feed | ✅ Works | `GET /api/feed`, `feed.js` |
| Community posts with file upload | ✅ Works | `POST /api/posts` (supports image+doc), `community.js` |
| Marketplace with images | ✅ Works | `POST /api/marketplace`, `marketplace.js` |
| Lost & found | ✅ Works | `public.py`, `lostandfound.js` |
| Announcements (admin-only) | ✅ Works | `POST /api/announcements` checks admin token |
| Institution directory | ✅ Works | `institutions.py`, `institutions.js` (600+ institutions) |
| Per-institution communities | ✅ Works | `InstitutionPost`, `institution_communities` |
| Campus events | ✅ Works | `campus.py`, `campus.js` |
| Jobs and internships | ✅ Works | `Opportunity` model, `campus.py`, `campus.js` |
| Reactions (like/celebrate/support) | ✅ Works (backend) | `campus.py`, `Reaction` model — **no UI in SPA** |
| Notifications | ✅ Works (backend) | `Notification` model, `GET/PUT /api/notifications` — **no UI in SPA** |
| Account registration/login | ✅ Works | `accounts.py`, `account.js` |
| Content reporting | ✅ Works | `POST /api/report`, admin resolves |
| Admin panel | ✅ Works | `admin.py`, `admin.js`, `templates/admin.html` |
| Advertiser portal | ✅ Works | `advertiser.py`, `advertiser.js`, `templates/advertiser.html` |
| Sponsored ads | ✅ Works | `Ad` + `Advertisement` models, `GET /api/ads/active` merges both |
| Ad performance tracking | ✅ Works | `ad_tracking.py`, impression/click/daily stats |
| File storage (local + Supabase) | ✅ Works | `storage.py` |
| Owner-token content editing | ✅ Works | `content_security.py` |
| Rate limiting | ✅ Works | `ratelimit.py` |
| Idempotency protection | ✅ Works | `IdempotencyRecord` + header pattern |
| PWA (manifest + SW) | ✅ Works | `static/manifest.json`, `static/sw.js` |
| Mobile bottom nav | ✅ Works | `#bottom-nav` with responsive sidebar at ≥900px |

### Needs to be added (new features)

| Feature | Priority per Spec | Backend Needed | Frontend Needed | Notes |
|---------|------------------|----------------|-----------------|-------|
| Dynamic homepage dashboard | High | `GET /api/dashboard` aggregating all sections | New `renderHomeDashboard()`, homepage grid layout | Replaces current feed-on-load behavior |
| Groups (Campus groups) | High | Group model, routes | `renderGroups()`, create/join UI | Nav button exists, crashes on click |
| Accommodation / Rooms | High | Accommodation/Hostel model | `renderAccommodation()` | Nav button exists, crashes on click |
| Scholarships | High | Add `scholarship` to `Opportunity.opportunity_type` validation | Update form type selector | 2-line backend change + frontend label |
| Industrial attachments | High | Add `attachment` to `Opportunity.opportunity_type` | Update form | Same as above |
| Roommate finder | Medium | RoommateListing model | UI section | Could reuse Accommodation section |
| Private messaging | Medium | Message/Conversation model | Messaging UI | Requires account auth |
| User profile page | Medium | No new backend needed | Profile view using `/api/accounts/me` | `showMyPosts()` is a stub |
| Notifications UI | Medium | Backend exists | Bell icon, notification panel | `GET/PUT /api/notifications` ready |
| Reactions UI | Medium | Backend exists | Like/react buttons on cards | `POST /api/reactions` ready |
| Learning hub | Medium | Could reuse `Post` with `topic='Study Material'` or new model | Dedicated section with file filter | File upload already works |
| Nearby services | Low | NearbyService model or Google Maps integration | Map/list UI | Needs location data |
| Global search | Medium | `GET /api/search?q=` aggregating all models | Wire `#global-search` input | Search bar in HTML, no handler |
| Business profiles | Medium | Public Advertiser profile routes | Business directory section | Advertiser model exists |
| Password reset | Medium | Email token model + `Flask-Mail` | Reset form | No email library installed |
| Email verification | Low | Verification token model + `Flask-Mail` | Verification flow | No email library installed |
| Google sign-in | Low | `authlib` or `flask-dance` | OAuth button | No OAuth library installed |
| Trending posts algorithm | Low | Score/weight query | Trending section in dashboard | Requires query redesign |
| M-Pesa integration | Low | Payment webhook | (admin-side) | Out of scope for this pass |

### Needs to be improved (exists but broken or incomplete)

| Issue | Location | Fix Needed |
|-------|---------|-----------|
| `groups` and `accommodation` nav buttons crash JS | `app.js` navigate router | Add stub `renderGroups()`/`renderAccommodation()` or remove nav buttons |
| `global-search` not wired | `app.js` / `index.html` | Add `input` event listener, call a search handler |
| `api()` doesn't send `X-Account-Token` | `app.js` | Add account token injection alongside admin token |
| Reactions have no UI | `campus.js`, `community.js`, `feed.js` | Add like/react buttons to post/event/opportunity cards |
| Notifications have no UI | No JS file | Add bell icon in header, notification panel |
| `showMyPosts()` is a stub | `account.js` | Implement profile view |
| No `GET /api/posts/<id>` route | `public.py` | Add single-post fetch to avoid reloading full page-1 for modal |
| `InstitutionPostComment` missing `poster_name` column in model | `models.py` | Add `poster_name = db.Column(db.String(100))` to `InstitutionPostComment` |
| Orphaned `poster_name` statement in `InstitutionPost.to_dict()` | `models.py` line ~148 | Remove the stray line |
| `AdCampaign` missing closing `)` on `advertiser_id` FK | `models.py` | Fix syntax (app likely uses `.pyc`; ensure source matches) |
| Marketplace has no search/filter UI | `marketplace.js` | Add search bar and category filter (backend supports it) |
| Opportunities has no type filter UI | `campus.js` | Add type filter (internship/job/scholarship) |
| Account token not persisted across page load correctly | `account.js` | Verify and fix token refresh on `DOMContentLoaded` |
| Feed doesn't include events or opportunities | `public.py` `get_feed()` | Add events and opportunities to feed aggregation |
| Admin stats panel not surfaced in admin UI | `admin.js` | Add stats/overview tab |

---

## 14. What is Out of Scope for a Single Implementation Pass

The following are complex enough to warrant separate dedicated passes:

- **Private messaging** — requires a full message/conversation data model, real-time delivery (WebSocket or polling), UI threads, and read receipts. This is a major feature.
- **Email verification and password reset** — requires adding an email library (`Flask-Mail` or SendGrid), new DB tables for verification/reset tokens, and email templates. The hosting environment (Render) must be configured with SMTP credentials.
- **Google sign-in** — requires `authlib`, OAuth2 flow, handling existing accounts with matching email, and secure token storage.
- **Nearby services** — requires either a curated data model (significant data entry work) or integration with Google Places API (API key, billing, frontend Maps SDK).
- **M-Pesa integration** — requires Safaricom Daraja API credentials, callback endpoint, payment reconciliation logic, and testing in a sandbox.
- **Real-time notifications** — requires WebSocket support (`flask-socketio`) and a frontend connection manager.
- **Full-text global search** — requires either PostgreSQL `tsvector` indices (Alembic migration) or a dedicated search service.
- **Trending algorithm** — requires a scoring table and background job or query that weights recency + engagement. No background task runner exists.

---

## 15. Conclusions and Recommendations

### Recommended implementation order for this pass

1. **Fix active JS bugs first** — add stub functions for `renderGroups()` and `renderAccommodation()` so those nav buttons don't crash. Wire `global-search` to a basic handler.

2. **Fix model bugs** — remove orphaned `poster_name` line from `InstitutionPost.to_dict()`, add `poster_name` column to `InstitutionPostComment`, fix `AdCampaign` syntax.

3. **Homepage dynamic dashboard** — replace the default `navigate('feed')` call with a `renderDashboard()` function that shows real content in sections: trending posts, recent marketplace listings, upcoming events, latest opportunities, announcements. All data is available from existing API endpoints; this is a frontend task.

4. **Add scholarships and industrial attachments** — two-line change to `campus.py` validation (`opportunity_type not in {'job', 'internship', 'scholarship', 'attachment'}`), plus form update.

5. **Wire reactions UI** — add like buttons to post and event cards. Backend is ready.

6. **Wire notifications UI** — add a bell icon to the account bar; pull from `GET /api/notifications`.

7. **Build Groups section** — minimal: a group model, create/join/post flow. Can share the institution-community pattern.

8. **Build Accommodation section** — a simple `Accommodation` model with landlord contact, monthly rent, location, images. Reuses marketplace UI patterns.

9. **User profile page** — replace `showMyPosts()` stub with a real profile view: name, bio, institution, posts by this user (requires a `GET /api/posts?author_account_id=` parameter or owner-token-based filtering).

10. **Global search** — add `GET /api/search?q=` that queries posts, marketplace, opportunities, events, and institutions, returning mixed results.

11. **CSS/UI redesign** — the CSS variables and card structure are already in good shape. The main homepage redesign work is building the dashboard layout (a grid of sections) and improving card visual design.

### Architecture notes for the implementer

- The app is a true SPA: one HTML page, section-based navigation in vanilla JS. No React/Vue — keep it that way.
- All new sections follow the same pattern: `render<Section>()` function in a new JS file, registered in `app.js` navigate router, FAB wired if the section has a create action.
- New backend features go in new Blueprints (e.g. `app/groups.py`, `app/accommodation.py`) registered in `__init__.py`.
- New DB tables require Alembic migrations (`flask db migrate && flask db upgrade`).
- File uploads already work through `storage.py`; reuse `upload_asset()` for any new image-bearing models.
- The `X-Account-Token` injection gap in `api()` must be fixed before reactions/notifications UI can work correctly from the shared `api()` helper.
