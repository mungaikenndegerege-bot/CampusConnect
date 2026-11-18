# Requirements: CampusConnect Advertiser Dashboard and Analytics System

## Summary

Build a complete advertiser management and analytics system inside the existing CampusConnect Flask application. The system adds four new capabilities: (1) a self-service advertiser portal where businesses register, create campaign requests with creatives and placements, and view analytics; (2) real impression and click tracking connected to the live frontend; (3) an analytics layer that aggregates event data into daily stats and serves them to dashboards; and (4) admin controls for approving advertisers and campaigns, managing placements and pricing, and reviewing revenue.

The existing `Ad` model, `GET /api/ads/active`, `POST /api/ads/<id>/click`, and all other existing routes, models, and templates must remain unchanged and fully functional throughout.

---

## Assumptions

**A1 — Database persistence:** The audit confirms that Render uses an ephemeral SQLite filesystem; every deploy wipes data. For a system that records advertiser payments, this is a critical risk. This requirements document assumes a persistent database will be attached before the advertiser system goes live (Render persistent disk or Render PostgreSQL). The implementation can proceed with SQLite locally, but deployment without persistence is explicitly out of scope for the payment and campaign data features.

**A2 — No email verification at launch:** Advertiser registration does not send a confirmation email at launch because no mail library is currently installed and the audit lists no SMTP configuration. Admin approval of the account acts as the verification gate. Email notifications are listed as a future enhancement.

**A3 — No PDF export at launch:** The original request mentions PDF reports. The audit confirms no PDF library is installed. CSV export (using stdlib `csv`) ships at launch; PDF export is deferred to a follow-up once a library choice (`reportlab` or `weasyprint`) is confirmed.

**A4 — Chart.js from CDN:** The advertiser portal will load Chart.js from `cdn.jsdelivr.net`. No Python charting library is needed.

**A5 — Single admin account:** The existing single-admin model is preserved. Advertiser token auth is a separate system (`X-Advertiser-Token` header) and does not interact with `X-Admin-Token`.

**A6 — No institution-level targeting in v1:** The original request mentions institution-level audience targeting. Because institutions are not yet linked to user accounts and no targeting signal exists, institution-level ad targeting is deferred. Placement selection (Feed Banner, Institution Community, etc.) is included as a placement label, but ads are not filtered per-institution in the feed.

**A7 — Admin credentials:** The hardcoded admin credentials (`Adminmungai` / `Mungai2300`) are not changed as part of this feature; that is a separate security hardening task. The requirement that admin credentials move to environment variables is noted but out of scope for this implementation.

---

## Functional Requirements

### FR-1: Advertiser Account Management

**FR-1.1** A business can submit a registration request with: `business_name` (required), `contact_name` (required), `email` (required, unique), `phone` (optional), `password` (required), `website` (optional), `description` (optional).

**FR-1.2** Passwords are hashed with Werkzeug's `generate_password_hash` (already used by the `Account` model) before storage.

**FR-1.3** A registered advertiser account starts with `status = 'pending'` and cannot create campaigns until the admin approves it (`status = 'approved'`).

**FR-1.4** An approved advertiser can log in with email and password and receives a session token (64-character hex string stored in `AdvertiserSession`). Tokens expire after 30 days.

**FR-1.5** All advertiser-facing API routes require the `X-Advertiser-Token` header. Routes return `401` if the token is absent, invalid, or expired.

**FR-1.6** An advertiser can log out, which deletes their session token from `AdvertiserSession`.

**FR-1.7** An advertiser can view and update their own profile (`business_name`, `contact_name`, `phone`, `website`, `description`). Email and password updates are not supported in v1.

### FR-2: Ad Placements

**FR-2.1** The system maintains a table of ad placements with: `name`, `description`, `price_per_day` (KSh), `active` flag.

**FR-2.2** The admin can create, edit, and activate/deactivate placements via the admin dashboard.

**FR-2.3** An approved advertiser can list available (active) placements and their prices.

**FR-2.4** The seed script creates four default placements: Feed Banner (KSh 500/day), Institution Community (KSh 300/day), Homepage Top (KSh 800/day), Sidebar (KSh 200/day).

### FR-3: Campaign and Advertisement Management (Advertiser)

**FR-3.1** An approved advertiser can create a campaign by submitting: `name`, `start_date`, `end_date`, `placement_id`, advertisement `title`, `body` (optional), `link_url` (optional), and an optional image file. One campaign contains one advertisement at creation.

**FR-3.2** A newly created campaign has `status = 'pending'` and `payment_status = 'unpaid'`. Its advertisement has `status = 'pending'`.

**FR-3.3** The system calculates `total_budget = price_per_day × (end_date − start_date + 1)` and stores it on the campaign.

**FR-3.4** An advertiser can view a list of all their own campaigns, including status, dates, budget, and aggregated stats (impressions, clicks, CTR).

**FR-3.5** An advertiser can view the detail of a single campaign, including the advertisement details and daily stats breakdown.

**FR-3.6** An advertiser can download a CSV report for a campaign from `GET /api/advertiser/campaigns/<id>/report`. The CSV contains one row per day with date, impressions, unique_reach, clicks, and CTR.

**FR-3.7** An advertiser cannot view, modify, or access any other advertiser's campaigns or data.

### FR-4: Campaign and Advertiser Management (Admin)

**FR-4.1** The admin can list all advertisers with their status and can approve or reject individual advertiser accounts.

**FR-4.2** The admin can list all campaigns across all advertisers and can approve, reject, pause, or activate individual campaigns.

**FR-4.3** When the admin approves a campaign, all associated advertisements are set to `status = 'approved'`.

**FR-4.4** When the admin activates a campaign, the campaign `status` becomes `'active'` and its ads become `'active'`.

**FR-4.5** When the admin pauses a campaign, the campaign `status` becomes `'paused'` and its ads become `'paused'`.

**FR-4.6** The admin can list all payments and confirm individual payments (setting `status = 'confirmed'` and `confirmed_at` timestamp).

**FR-4.7** The admin can view an overall revenue summary: total confirmed revenue, total unpaid campaigns, and total paid campaigns.

### FR-5: Impression Tracking

**FR-5.1** The backend exposes `POST /api/track/impression` accepting `{ advertisement_id, placement }`. The endpoint records a qualifying impression event in `AdImpression` and updates `AdDailyStat` for today.

**FR-5.2** Deduplication: a `visitor_hash` is computed server-side as `sha256(ip_address + current_date_string)[:16]`. If an `AdImpression` row already exists for the same `advertisement_id` and `visitor_hash` today, the duplicate is silently dropped and the endpoint returns `200 OK` without recording.

**FR-5.3** Bot filtering: if the request `User-Agent` header matches any of these strings (case-insensitive): `googlebot`, `bingbot`, `facebookexternalhit`, `python-requests`, `curl`, `wget`, `headless` — the endpoint returns `200 OK` without recording.

**FR-5.4** Rate limiting: a maximum of 100 impression events per IP address per hour is enforced using the existing `check_rate_limit` decorator pattern. Requests over the limit return `200 OK` without recording (silent drop to avoid revealing the limit to scrapers).

**FR-5.5** After recording an impression, the endpoint upserts `AdDailyStat` for `(advertisement_id, campaign_id, today)`: incrementing `impressions` and updating `unique_reach` as the count of distinct `visitor_hash` values for that ad today.

**FR-5.6** An impression is only recorded if the target `Advertisement` has `status = 'active'` and its campaign's current date falls within `[start_date, end_date]`. Attempts to record impressions against inactive or expired ads return `200 OK` without recording.

**FR-5.7** The frontend tracks impressions using `IntersectionObserver` with a 50 % visibility threshold, a minimum 1-second dwell, and a per-session `Set` to prevent double-firing after the first qualifying view.

### FR-6: Click Tracking

**FR-6.1** The backend exposes `POST /api/track/click/<advertisement_id>`. It validates the destination URL, records a row in `AdClick`, updates `AdDailyStat.clicks` for today, and returns `{ redirect_url }`.

**FR-6.2** URL validation: `link_url` must start with `http://` or `https://` and must not contain the string `/admin` or `/api/admin`. Invalid or empty URLs return `400`.

**FR-6.3** The frontend ad click handler calls `/api/track/click/<id>` and opens `data.redirect_url` in a new tab. The existing `POST /api/ads/<id>/click` endpoint on the old `Ad` model is preserved for backward compatibility.

**FR-6.4** Each click row stores: `advertisement_id`, `campaign_id`, `visitor_hash`, `placement`, `destination_url`, `recorded_at`.

### FR-7: Analytics

**FR-7.1** `GET /api/advertiser/campaigns/<id>/stats` returns: total `impressions`, `unique_reach`, `clicks`, `ctr` (clicks / impressions × 100, rounded to two decimal places, 0 if impressions = 0), and a `daily` array of `{ date, impressions, clicks }` objects ordered by date ascending.

**FR-7.2** Stats are read from `AdDailyStat`; they are never computed from raw impression/click rows on each request to keep query time constant as event volume grows.

**FR-7.3** The advertiser dashboard displays stat cards for: total impressions, total clicks, CTR, and active campaign count. It also shows a Chart.js line chart of daily impressions and clicks for the selected campaign.

**FR-7.4** The admin revenue endpoint `GET /api/admin/revenue` returns: `total_campaigns`, `confirmed_revenue` (sum of `AdPayment.amount` where `status = 'confirmed'`), `unpaid_campaigns` (count of campaigns with `payment_status = 'unpaid'`), `paid_campaigns`.

### FR-8: Ad Serving (GET /api/ads/active Extension)

**FR-8.1** `GET /api/ads/active` continues to return all legacy `Ad` records where `active = True`.

**FR-8.2** The endpoint also appends active `Advertisement` records where `status = 'active'` and today falls within the campaign's `start_date` to `end_date`. Each is serialised to the same dict shape used by the legacy `Ad` model so the frontend needs no changes to `injectAds`.

**FR-8.3** The serialised `Advertisement` record includes an `ad_type: 'campaign'` field to distinguish it from legacy `Ad` records (which carry `ad_type: 'legacy'` or no field). The frontend ignores unknown fields.

### FR-9: Advertiser Portal (Frontend)

**FR-9.1** A new page is served at `GET /advertiser` (and `/advertiser/`) rendering `templates/advertiser.html`.

**FR-9.2** `advertiser.html` loads `/static/css/advertiser.css` and `/static/js/advertiser.js`.

**FR-9.3** The portal is a single-page application with these screens: Login/Register, Dashboard (stat cards + recent campaigns), Campaign List, New Campaign form, Campaign Detail (stats + daily chart + CSV download), and Settings (profile update).

**FR-9.4** The portal uses purple `#6C3CE1` as primary colour and gold `#F5A623` as accent colour, with a white background. It is responsive: sidebar navigation on desktop, tab navigation on mobile.

**FR-9.5** Chart.js is loaded from `https://cdn.jsdelivr.net/npm/chart.js` by dynamic script injection when the Campaign Detail screen is opened.

**FR-9.6** The portal stores the advertiser session token in `localStorage` under a key distinct from the admin token key (`cc_adv_token`).

### FR-10: Admin Dashboard Extensions

**FR-10.1** `templates/admin.html` gains five new tab buttons: Advertisers, Campaigns, Placements, Revenue, Payments.

**FR-10.2** `static/js/admin.js` gains corresponding tab-load functions using the existing `adminApi` helper and `escHtml` utility.

**FR-10.3** The Advertisers tab shows a table of all advertiser accounts with status badges and Approve/Reject action buttons.

**FR-10.4** The Campaigns tab shows all campaigns across advertisers with status badges and Approve/Reject/Pause/Activate action buttons.

**FR-10.5** The Placements tab shows the placement list and a form to create a new placement or edit an existing one (name, description, price_per_day, active toggle).

**FR-10.6** The Revenue tab shows the confirmed revenue total, unpaid campaign count, and paid campaign count.

**FR-10.7** The Payments tab shows all payment records with a Confirm button for payments in `pending` status.

---

## Non-Functional Requirements

**NFR-1 — Backward compatibility:** No existing route, model, template, or JavaScript function may be removed or renamed. All existing features must continue to work after the changes.

**NFR-2 — Advertiser data isolation:** An authenticated advertiser must only be able to read and write records that belong to their own `advertiser_id`. The backend must enforce this at the query level, not only at the UI level.

**NFR-3 — No personal user data exposure:** Advertiser analytics must only expose aggregated stats. `visitor_hash` values are never returned to the advertiser; `AdImpression` and `AdClick` raw rows are internal only.

**NFR-4 — No new Python packages required:** The spec requires only stdlib `hashlib` for visitor hashing and stdlib `csv` for CSV export. No new entries are needed in `requirements.txt` for the core feature set (PDF export, if added later, would require `reportlab`).

**NFR-5 — SQLite compatibility:** All new models use data types compatible with SQLite. No PostgreSQL-specific types are used, so the system works locally and transitions to PostgreSQL without model changes.

**NFR-6 — `db.create_all()` schema management:** The project uses no migration tool. All new tables are defined as SQLAlchemy models so `db.create_all()` in `seed.py` picks them up on the next start or deploy.

**NFR-7 — Tracking endpoint latency:** Impression and click endpoints must complete within 200 ms under normal load. The dedup check and daily-stat upsert must run in a single database transaction.

**NFR-8 — Kenyan data protection:** `visitor_hash` is derived from IP + date and is not reversible to the original IP. Raw IP addresses are not stored in impression or click records. Retention policy for raw events is not enforced in v1 but is noted as a future requirement.

---

## Acceptance Criteria

### Authentication

**AC-1** `POST /api/advertiser/register` with valid fields returns `201` and a JSON body with `advertiser.id`. A second call with the same email returns `409`.

**AC-2** `POST /api/advertiser/register` without `business_name`, `contact_name`, `email`, or `password` returns `400`.

**AC-3** `POST /api/advertiser/login` with correct credentials for a `pending` advertiser returns a token AND a note that the account is awaiting approval (the advertiser can log in but cannot create campaigns).

**AC-4** `POST /api/advertiser/login` with correct credentials for an `approved` advertiser returns `200` with a `token` and `advertiser` object.

**AC-5** Any advertiser route called with an absent, expired, or invalid `X-Advertiser-Token` returns `401`.

### Admin Controls

**AC-6** `PUT /api/admin/advertisers/<id>/approve` with a valid admin token sets the advertiser's `status` to `'approved'` and returns `200`.

**AC-7** `PUT /api/admin/campaigns/<id>/approve` sets campaign `status` to `'approved'` and all associated advertisement records to `status = 'approved'`.

**AC-8** `PUT /api/admin/campaigns/<id>/activate` sets campaign `status` to `'active'` and all associated advertisement records to `status = 'active'`.

**AC-9** `PUT /api/admin/payments/<id>/confirm` sets payment `status` to `'confirmed'` and records `confirmed_at`.

### Campaign Management

**AC-10** `POST /api/advertiser/campaigns` by a `pending` advertiser (not yet approved) returns `403`.

**AC-11** `POST /api/advertiser/campaigns` by an `approved` advertiser with valid fields returns `201` and a campaign object with `status = 'pending'` and computed `total_budget`.

**AC-12** `GET /api/advertiser/campaigns` returns only campaigns belonging to the authenticated advertiser — not campaigns from any other advertiser.

**AC-13** `GET /api/advertiser/campaigns/<id>` returns `403` if the campaign belongs to a different advertiser.

### Impression Tracking

**AC-14** `POST /api/track/impression` with a valid `advertisement_id` for an active advertisement records one `AdImpression` row and returns `200`.

**AC-15** A second `POST /api/track/impression` from the same IP on the same day for the same `advertisement_id` returns `200` but records no additional `AdImpression` row (deduplication confirmed by checking `AdImpression` count before and after).

**AC-16** `POST /api/track/impression` with `User-Agent: Googlebot/2.1` records no impression and returns `200`.

**AC-17** `POST /api/track/impression` targeting an `advertisement_id` whose campaign has expired (today > `end_date`) records no impression and returns `200`.

**AC-18** After a qualifying impression is recorded, the corresponding `AdDailyStat.impressions` for today increments by 1.

### Click Tracking

**AC-19** `POST /api/track/click/<id>` for an active advertisement records one `AdClick` row, increments `AdDailyStat.clicks` for today, and returns `{ redirect_url }`.

**AC-20** `POST /api/track/click/<id>` where `link_url` is empty or not `http/https` returns `400`.

**AC-21** `POST /api/track/click/<id>` where `link_url` contains `/api/admin` returns `400`.

**AC-22** The existing `POST /api/ads/<id>/click` endpoint still returns `200` and increments `Ad.click_count` on a legacy `Ad` record.

### Ad Serving

**AC-23** `GET /api/ads/active` returns a JSON array that includes both legacy `Ad` records (where `active = True`) and active `Advertisement` records within their campaign date range.

**AC-24** The array items for `Advertisement` records carry the same keys used by legacy records (`id`, `title`, `body`, `image_path`, `link_url`) so that the existing `renderAdBanner` function renders them without modification.

### Analytics

**AC-25** `GET /api/advertiser/campaigns/<id>/stats` returns `{ impressions, unique_reach, clicks, ctr, daily: [...] }` with `ctr` computed as `clicks / impressions * 100` (0.0 when impressions = 0).

**AC-26** `GET /api/advertiser/campaigns/<id>/report` returns a file download with `Content-Disposition: attachment; filename="campaign_<id>_report.csv"` containing a header row and one data row per day in the campaign range.

### Frontend

**AC-27** `GET /advertiser` returns `200` with HTML containing `advertiser.js` and `advertiser.css` references.

**AC-28** The advertiser portal login screen is shown when `localStorage` does not contain a valid `cc_adv_token`. The dashboard screen is shown when a valid token is present.

**AC-29** An ad banner in the feed that is scrolled into 50 % visibility and held for 1 second fires exactly one `POST /api/track/impression` per page session per ad (confirmed via browser DevTools network log).

**AC-30** Clicking "Learn More" on a campaign advertisement calls `POST /api/track/click/<id>` and opens the `redirect_url` in a new tab.

### Placements Seed

**AC-31** Running `python seed.py` on a fresh database creates exactly four placement records: Feed Banner, Institution Community, Homepage Top, Sidebar.

**AC-32** Running `python seed.py` a second time does not create duplicate placements.

### Compile Check

**AC-33** `python -m py_compile app/models.py app/advertiser.py app/ad_tracking.py app/__init__.py` exits with code 0.

---

## Out of Scope

The following items are explicitly excluded from this implementation. They are captured here so they are not silently forgotten.

- **PDF report generation** — deferred pending `reportlab` or `weasyprint` package decision. CSV export ships instead.
- **Email notifications** — no SMTP configuration exists; advertiser registration confirmation and campaign approval emails are deferred.
- **Institution-level ad targeting** — requires linking institution membership to user accounts, which is not yet built.
- **Audience targeting beyond placement** — demographic, topic, or geographic targeting is deferred.
- **Campaign renewal workflow** — advertiser-initiated renewals are deferred; the advertiser can create a new campaign instead.
- **Conversion tracking** — the `ad_conversions` table concept is noted but no conversion event source exists yet; deferred.
- **Admin credential hardening** (move to env vars) — a separate security task; explicitly not changed in this feature.
- **Persistent database provisioning** — the choice and configuration of a persistent store (Render disk or PostgreSQL) must happen before production launch but is an infrastructure task, not a code task.
- **Rate limiting advertiser registration** — deliberately omitted in v1; to be added with the broader rate-limit review.
- **Campaign comparison view** — the original request mentions comparing campaigns side by side; deferred to a later analytics iteration.
- **Date-range filters on analytics** (Today / Last 7d / Last 30d / Last 90d / Custom) — the stats endpoint returns all daily data; the frontend can filter client-side, but server-side date-range parameters are not implemented in v1.
- **Suspicious activity detection dashboard** — the original request mentions an admin view for identifying suspicious traffic; deferred.
- **React Native mobile app integration** — the backend tracking API is mobile-compatible (HTTP POST with JSON), but no mobile SDK or documentation is produced in this phase.
