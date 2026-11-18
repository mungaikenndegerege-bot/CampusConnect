# Design Review: CampusConnect Advertiser Dashboard and Analytics System

**Document reviewed:** `02-design.md`  
**Requirements:** `01-requirements.md`  
**Source verified against:** `c:\Users\user\Documents\NetBeansProjects\CampusConnect`  
**Verdict:** CHANGES_REQUESTED

---

## Findings

### Finding 1 — HIGH: `check_rate_limit` returns `429`, design claims silent `200` drop

**Where:** Design §3, `POST /api/track/impression` description; also the error table row "Rate limit exceeded → `429` (from decorator)".

**Problem:** The design states in FR-5.4 (requirements) that rate-limited impression requests should return `200 OK` (silent drop to avoid revealing the limit to scrapers). The design document itself contradicts this in the error table where it says the decorator returns `429`. Worse, the actual `check_rate_limit` decorator in `app/ratelimit.py` always returns `429` with a JSON error message:

```python
return jsonify({'error': 'Too many requests. Please wait before posting again.'}), 429
```

There is no way for the impression endpoint to silently absorb the rate-limit hit by using `@check_rate_limit` as written. The decorator fires and returns before the function body executes, so the function body cannot suppress it.

**Concrete fix:** Either (a) do not use `@check_rate_limit` on the impression endpoint and implement IP-based rate limiting inside the function body (where a silent drop is possible), or (b) add a `silent=True` parameter to `check_rate_limit` that returns `200 {'ok': True}` instead of `429`. Option (a) is simpler. Example inside the function body:

```python
# At top of impression handler, before bot detection:
ip = request.remote_addr or 'unknown'
now = datetime.utcnow().timestamp()
# use a module-level defaultdict for impression-specific rate tracking
with _imp_lock:
    _imp_hits[ip] = [t for t in _imp_hits[ip] if now - t < 3600]
    if len(_imp_hits[ip]) >= 100:
        return jsonify({'ok': True}), 200
    _imp_hits[ip].append(now)
```

---

### Finding 2 — HIGH: `app/ad_tracking.py` imports `check_rate_limit` from `app.ratelimit` but the design then says "decorated with `@check_rate_limit(100, 3600)`" — this contradicts the silent-drop requirement and creates an import that doesn't match usage

**Where:** Design §3, opening paragraph of `POST /api/track/impression`.

**Problem:** The design says the endpoint is "decorated with `@check_rate_limit(100, 3600)`" and separately says the rate limit returns `429 (from decorator)` — but FR-5.4 in requirements requires `200 OK` without recording. These three statements cannot all be true simultaneously. The requirement is authoritative; the design is contradictory. An implementer following the decorator literally violates FR-5.4 and AC requirement intent.

**Concrete fix:** Remove the `@check_rate_limit` decorator from the impression endpoint entirely. Keep the import of `check_rate_limit` only if it is actually used elsewhere in `ad_tracking.py` (it is not). Implement silent IP rate limiting inline as shown in Finding 1.

---

### Finding 3 — HIGH: `AdDailyStat` unique-reach recount reads uncommitted rows, inflating the count

**Where:** Design §3, step 7 of `POST /api/track/impression` upsert logic.

**Problem:** The design recomputes `unique_reach` by querying `AdImpression` for distinct `visitor_hash` values, then adds `+1` for "the row we just added (not yet committed)". This is incorrect. Within the same SQLAlchemy session, the newly added `AdImpression` row is in the session's identity map but has not been flushed to the database. Whether the `COUNT(DISTINCT ...)` query sees it depends on whether SQLAlchemy auto-flushes before the query (it does by default). This means:

- With auto-flush on (default): the new row **is** visible to the query, so the `+1` double-counts it. `unique_reach` will be 1 too high on every new unique visitor.
- With auto-flush off: the row is not visible, so the `+1` is correct — but the design doesn't state this.

**Concrete fix:** Either flush explicitly before the count query and remove the `+1`:

```python
db.session.flush()  # make the new AdImpression row visible
stat.unique_reach = db.session.query(
    db.func.count(db.func.distinct(AdImpression.visitor_hash))
).filter(
    AdImpression.advertisement_id == advertisement_id,
    AdImpression.recorded_at >= today_midnight
).scalar() or 0
# No +1 needed; the row is already counted above
```

Or, avoid the sub-query entirely and increment `unique_reach` only when the `visitor_hash` is genuinely new for today (which the dedup check already confirms — if execution reaches step 7, this is a new unique visitor for today, so simply `stat.unique_reach += 1`).

---

### Finding 4 — HIGH: `GET /api/advertiser/campaigns` list endpoint accesses `campaign.advertisements[0].placement.name` via lazy-loaded relationships — this triggers N+1 queries and will silently return empty strings when relationships are not loaded

**Where:** Design §2, "Campaign list screen" and "Backend addition for campaign list serialiser" note.

**Problem:** The design acknowledges this in a parenthetical ("relationships lazy-load on first access within the same session") but then accepts it as correct. For N campaigns, this triggers N queries for `advertisements` + N queries for `placement`, totalling 2N+1 queries for the list endpoint. For 50 campaigns that is 101 queries. Beyond performance: if `campaign.advertisements` is empty (which is impossible by design but could occur from data integrity issues), the code `campaign.advertisements[0].placement.name` raises `IndexError`, crashing with 500.

**Concrete fix:** Use an explicit join in the campaign list query:

```python
from sqlalchemy.orm import joinedload
campaigns = AdCampaign.query.filter_by(advertiser_id=session.advertiser_id)\
    .options(joinedload(AdCampaign.advertisements).joinedload(Advertisement.placement))\
    .order_by(AdCampaign.created_at.desc()).all()
```

Then access `campaign.advertisements[0].placement.name if campaign.advertisements else ''` safely. This collapses to 1–3 queries regardless of campaign count.

---

### Finding 5 — HIGH: `injectAds` replacement modifies `state.adIndex` for legacy ads but the existing `injectAds` does not distinguish ad types — the design's replacement breaks legacy ad cycling

**Where:** Design §10, "Replace `injectAds`" code block.

**Problem:** The design replaces `injectAds` with a version that pushes `injectedAdIds` only for `ad.ad_type === 'campaign'` ads, but increments `state.adIndex` for every ad (legacy or campaign). This matches the existing behaviour. However, the existing `injectAds` does not set `type: 'ad'` on the spread object — the design's replacement adds `{ ...ad, type: 'ad' }`. Looking at the actual `app.js`, the existing code already does `result.push({ ...ad, type: 'ad' })`. ✓ That part is consistent.

The real problem: the existing `renderAdBanner` has no `data-ad-id` attribute on the outer div, so `observeAdImpression` calling `document.querySelector('[data-ad-id="${adId}"]')` will find nothing for legacy ads. The design's new `renderAdBanner` adds `data-ad-id` and `data-ad-type` attributes. For legacy ads the click handler in the design uses a string interpolated directly into an `onclick` attribute:

```js
`fetch('/api/ads/${ad.id}/click',{method:'POST'})`
```

This hardcodes the fetch call in HTML. For campaign ads it uses `advTrackClick(${ad.id}, event)`. If `event` is the click event object, this works; `event` is the global `event` object in inline handlers in most browsers, but this is non-standard and fails in strict-mode modules. The design should use `onclick="advTrackClick(${ad.id})"` and not pass `event` through the HTML attribute. The `advTrackClick` function should call `event.preventDefault()` via the actual DOM event, not an argument. Since the `<a>` tag has `href` set to the original URL and `target="_blank"`, omitting `preventDefault` is actually correct (the browser handles the navigation after the fetch). The `event.preventDefault()` call in `advTrackClick` would suppress the browser's natural navigation, which means the click only works if the fetch succeeds and `window.open` fires. If the network is unavailable, the user gets no navigation at all.

**Concrete fix:** Remove `event.preventDefault()` from `advTrackClick`. Use `onclick="advTrackClick(${ad.id})"` without passing `event`. The `<a>` tag's natural `href` acts as fallback if the fetch fails:

```javascript
function advTrackClick(adId) {
  fetch(`/api/track/click/${adId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ placement: '' })
  })
    .then(r => r.json())
    .then(data => { if (data.redirect_url) window.open(data.redirect_url, '_blank'); })
    .catch(() => {});
  // Do NOT preventDefault — the href= attribute provides fallback navigation
}
```

And the template literal in `renderAdBanner`:
```js
onclick="advTrackClick(${ad.id})"
```

---

### Finding 6 — MEDIUM: `require_advertiser()` returns the `AdvertiserSession` object but the design uses `session.advertiser_id` without loading the `Advertiser` object — routes that need `advertiser.status` make an additional implicit query

**Where:** Design §2, `require_advertiser` guard function and `POST /api/advertiser/campaigns`.

**Problem:** The guard returns the `AdvertiserSession` row. Routes that check `advertiser.status != 'approved'` (e.g. campaign creation) must access `session.advertiser` (via SQLAlchemy backref) or call `Advertiser.query.get(session.advertiser_id)`. The design does not state which pattern is used. If the route does `session.advertiser.status`, that lazy-loads the `Advertiser` row, which is fine functionally but the design is silent about it. More importantly, the guard function is described as returning `None` on failure or the session on success, but routes check the return value with no explicit type annotation — an implementer might return only `session.advertiser_id` (an integer), which would silently pass a truthy value even when the session is expired (integer `> 0` is truthy). The design says `return session` but should be explicit that all protected routes access `session.advertiser_id` to get the ID and `session.advertiser.status` to get the status.

**Concrete fix:** Add a note that all protected routes use:
```python
adv_session = require_advertiser()
if not adv_session:
    return jsonify({'error': 'Unauthorized'}), 401
advertiser = adv_session.advertiser  # lazy-loaded; always present due to FK
```
And explicitly state that `advertiser` (not `adv_session`) is used for `status` checks.

---

### Finding 7 — MEDIUM: `POST /api/advertiser/campaigns` accepts `multipart/form-data` but date fields are parsed with `datetime.strptime` — form data values are always strings, so this works, but `placement_id` is read as a string and must be explicitly cast to `int`

**Where:** Design §2, `POST /api/advertiser/campaigns` route.

**Problem:** The design says "Accepts `multipart/form-data`" and reads `placement_id` as an integer: `placement_id (required, integer, must reference an active AdPlacement)`. With `multipart/form-data`, `request.form['placement_id']` returns a string. If the code does `AdPlacement.query.get(placement_id)` without converting to `int`, SQLAlchemy will attempt a query with a string primary key and either find nothing (silent failure — placement appears not found) or raise a type error depending on the SQLite driver. The design does not show the actual code for the `placement_id` lookup, leaving this implicit.

**Concrete fix:** Explicitly show the integer conversion:
```python
try:
    placement_id = int(request.form.get('placement_id', ''))
except (ValueError, TypeError):
    return jsonify({'error': 'placement_id must be an integer'}), 400
placement = AdPlacement.query.get(placement_id)
if not placement or not placement.active:
    return jsonify({'error': 'Invalid or inactive placement'}), 400
```

---

### Finding 8 — MEDIUM: `loadTab` function replacement in `admin.js` — the design says "replace one line" but the actual `loadTab` function in `admin.js` has the loaders dict on a single line; the edit instruction is correct, but the design shows the full replacement string without the trailing semicolons that exist in the file, risking a syntax error if the coder pastes it verbatim

**Where:** Design §12, `loadTab` loaders replacement.

**Problem:** The actual line in `admin.js` is:
```javascript
const loaders = { ads: loadAdsTab, announcements: loadAnnouncementsTab, posts: loadPostsTab, marketplace: loadMarketplaceTab, lostandfound: loadLFTab, reports: loadReportsTab, institutions: loadInstitutionsAdminTab };
```
The design's replacement snippet splits across two lines without a semicolon at the end. If the coder copies the two-line version verbatim (without a terminating `}`+`;`), the object literal is not closed. The design should show the complete, syntactically valid replacement.

**Concrete fix:**
```javascript
const loaders = {
  ads: loadAdsTab, announcements: loadAnnouncementsTab, posts: loadPostsTab,
  marketplace: loadMarketplaceTab, lostandfound: loadLFTab, reports: loadReportsTab,
  institutions: loadInstitutionsAdminTab, advertisers: loadAdvertisersTab,
  adcampaigns: loadAdCampaignsTab, placements: loadPlacementsTab,
  revenue: loadRevenueTab, payments: loadPaymentsTab
};
```

---

### Finding 9 — MEDIUM: `AdvertiserSession` has no expiry enforced on the model side; `require_advertiser()` uses a `created_at >= cutoff` filter, but there is no index on `AdvertiserSession.token` — every token lookup is a full table scan

**Where:** Design §1, `AdvertiserSession` model definition.

**Problem:** The `AdminSession` model in `app/models.py` defines `token = db.Column(db.String(64), unique=True, index=True, ...)`. The design's `AdvertiserSession` model defines `token = db.Column(db.String(64), unique=True, nullable=False)` — no `index=True`. With many active sessions (which is likely given 30-day expiry vs admin's 24-hour expiry), every impression or click request that calls `require_advertiser()` performs a full table scan. This is a NFR-7 violation risk (200 ms budget).

**Concrete fix:** Add `index=True` to the token column:
```python
token = db.Column(db.String(64), unique=True, index=True, nullable=False)
```

---

### Finding 10 — MEDIUM: `GET /api/advertiser/campaigns/<id>/report` iterates calendar days from `start_date` to `end_date` but the design does not specify the iteration mechanism — `(end_date - start_date).days + 1` gives the count, not the dates

**Where:** Design §2, `GET /api/advertiser/campaigns/<id>/report`.

**Problem:** The design says "iterates `(end_date - start_date).days + 1` times" but does not show how to generate the actual date sequence. A naive range loop over integers loses the date values. An implementer might write `for i in range(total_days): day = start_date + timedelta(days=i)` — which is correct — but the design does not specify this. Without the `timedelta` import shown explicitly in the new files, an implementer might omit it.

**Concrete fix:** Show the loop explicitly:
```python
from datetime import timedelta
days = (campaign.end_date - campaign.start_date).days + 1
stat_map = {s.date: s for s in AdDailyStat.query.filter_by(campaign_id=id).all()}
for i in range(days):
    day = campaign.start_date + timedelta(days=i)
    s = stat_map.get(day)
    imps  = s.impressions   if s else 0
    reach = s.unique_reach  if s else 0
    clks  = s.clicks        if s else 0
    ctr   = round(clks / imps * 100, 2) if imps else 0.0
    writer.writerow([day.isoformat(), imps, reach, clks, ctr])
```

---

### Finding 11 — MEDIUM: URL validation in `POST /api/track/click/<id>` checks `'/admin'` in `url.lower()` but this blocks legitimate destinations containing the word "admin" (e.g. `https://college.ac.ke/administration`)

**Where:** Design §3, step 3 of click handler; also FR-6.2 in requirements.

**Problem:** FR-6.2 says URLs must not contain `/api/admin`. The design checks `'/admin'` (without the `/api` prefix), which is broader than the requirement. `https://example.com/admin-panel` is a legitimate advertiser destination and would be incorrectly rejected. The requirements document uses the more precise string `/api/admin`.

**Concrete fix:** Use the requirement's exact string:
```python
if '/api/admin' in url.lower():
    return jsonify({'error': 'Invalid destination URL'}), 400
```

---

### Finding 12 — MEDIUM: `AdDailyStat` unique constraint `uq_ad_daily` is on `(advertisement_id, date)` but `GET /api/advertiser/campaigns/<id>/stats` queries by `campaign_id` — no index on `(campaign_id)` in `AdDailyStat`

**Where:** Design §1, `AdDailyStat` model; Design §2, `GET /api/advertiser/campaigns/<id>/stats`.

**Problem:** `AdDailyStat.query.filter_by(campaign_id=id)` has no supporting index. For campaigns with many advertisements and long durations, this becomes a full table scan. The stats endpoint is called on every Campaign Detail view load.

**Concrete fix:** Add a composite index on `(campaign_id, date)`:
```python
__table_args__ = (
    db.UniqueConstraint('advertisement_id', 'date', name='uq_ad_daily'),
    db.Index('ix_adstat_campaign_date', 'campaign_id', 'date'),
)
```

---

### Finding 13 — MEDIUM: The design does not specify how `AdPayment` records are created — there is no advertiser or admin route that creates an `AdPayment` row, yet the Revenue and Payments admin tabs expect to list and confirm payment records

**Where:** Design §4, revenue and payments routes; FR-4.6 and FR-4.7 in requirements.

**Problem:** `GET /api/admin/payments` and `PUT /api/admin/payments/<id>/confirm` assume `AdPayment` rows exist. No route in `app/advertiser.py` or `app/admin.py` creates an `AdPayment` record. The design describes no mechanism by which a payment record comes into existence. The advertiser portal has no "submit payment" button or M-Pesa integration point. The admin cannot confirm payments that were never recorded.

**Concrete fix:** Define the payment creation point. The simplest approach consistent with the design's scope (no live payment gateway) is to create an `AdPayment` row automatically when a campaign is created:
```python
# At the end of POST /api/advertiser/campaigns, after campaign commit:
payment = AdPayment(
    campaign_id=campaign.id,
    amount=budget,
    payment_method='manual',
    status='pending'
)
db.session.add(payment)
db.session.commit()
```
State this explicitly in the design and add a note to the advertiser dashboard explaining that payment confirmation is done offline (bank transfer reference sent to admin).

---

### Finding 14 — NIT: Design §1 says "the last existing model" is `InstitutionPostComment` — this is correct per the source code, but the description should be verified — it is confirmed.

No action needed.

---

### Finding 15 — NIT: `renderAdBanner` in design §10 uses `${escHtml(ad.link_url)}` as the `href` attribute value, which HTML-encodes the URL — this will double-encode ampersands in query strings (`&` becomes `&amp;amp;` after two passes)

**Where:** Design §10, `renderAdBanner` template literal.

**Problem:** `href="${escHtml(ad.link_url)}"` replaces `&` with `&amp;` in the URL. For URLs like `https://example.com/page?ref=camp&id=1`, the browser will receive `href="https://example.com/page?ref=camp&amp;id=1"` which parses correctly as HTML (HTML entities in `href` are decoded by the parser). This is actually the correct HTML practice. No change needed — the existing `renderAdBanner` does the same thing. This is a non-issue.

---

### Finding 16 — NIT: `seed.py` changes — the design appends code after `seed_institutions()` but the design does not import `app` or `db` for the new placement seeding block; it assumes the existing `seed.py` context provides them

**Where:** Design §6, seed.py changes.

**Problem:** The existing `seed.py` does `with app.app_context():` and then calls `seed_institutions()`. The new placement seeding code runs `db.session.add(...)` and `db.session.commit()`. As long as the new code is inside the existing `with app.app_context():` block, `db` is accessible via the import at the top. The design's snippet does not show its indentation context. The implementer must indent the new block inside the existing `with` block.

**Concrete fix:** Show the indentation explicitly in the design diff, or explicitly state "append inside the `with app.app_context():` block."

---

### Finding 17 — NIT: The design imports `AdCampaign` via local imports inside `get_active_ads` using the alias `from app.models import Advertisement, AdCampaign` — but `AdCampaign` is not defined yet in `models.py` before this change; the local import ensures it only runs after models are loaded

**Where:** Design §3, `get_active_ads` replacement.

**Problem:** The design notes "local imports avoid adding to top-level imports" but does not explain that this is also required because `app/public.py` is loaded before `app/advertiser.py` registers the new models. Actually, all models are defined in `app/models.py` and all are loaded together by `db.create_all()`. The local import is a stylistic choice, not a requirement. It is fine as described; this is informational only.

---

## Verified Assumptions

The following design claims were checked against source and are correct:

- **`check_rate_limit` exists in `app/ratelimit.py`** ✓ — Present at the stated path, with the `@check_rate_limit(max_requests, window_seconds)` signature.
- **`save_upload` helper exists in `app/admin.py` and `app/public.py`** ✓ — Both files define a `save_upload(file)` function. The design copies it into `advertiser.py` to avoid cross-blueprint imports; this is correct.
- **`escHtml` utility exists in `admin.js`** ✓ — Confirmed at line 12 of `admin.js`.
- **`adminApi` helper exists in `admin.js`** ✓ — Confirmed; the design's `advApi` correctly mirrors its structure.
- **`loadTab` and its `loaders` dict exist in `admin.js`** ✓ — The exact line `const loaders = { ads: loadAdsTab, ... }` is present and matches what the design proposes to replace.
- **`renderAdBanner` function exists in `app.js`** ✓ — Present with the exact structure the design proposes to replace.
- **`injectAds` function exists in `app.js`** ✓ — Present with the same logic the design extends.
- **`Ad` model in `models.py` has `click_count` field** ✓ — Confirmed.
- **`from datetime import datetime` (not `datetime, date`) is the current import in `models.py`** ✓ — The design correctly identifies that `date` must be added.
- **`InstitutionPostComment` is the last model in `models.py`** ✓ — Confirmed.
- **Admin credentials are `Adminmungai` / `Mungai2300`** ✓ — Present in `admin.py`.
- **No PDF library in `requirements.txt`** ✓ — `requirements.txt` lists only Flask, Flask-SQLAlchemy, Flask-CORS, Werkzeug, gunicorn, python-dotenv.
- **`werkzeug.security` is available** ✓ — Werkzeug 3.0.3 is installed.
- **`render.yaml` already runs `python seed.py` as a build command** ✓ — Confirmed.
- **`Dockerfile` already runs `python seed.py`** ✓ — Confirmed.
- **`__init__.py` registers blueprints using local imports inside `create_app()`** ✓ — The institutions blueprint uses this pattern; the design correctly follows it.
- **`feed.js` calls `renderAdBanner` for `item.type === 'ad'` items** ✓ — Confirmed in `feed.js` `renderFeed` function.
- **Admin `openModal` is defined in `admin.js` itself** ✓ — Confirmed; the design correctly notes admin.html doesn't use app.js's modal.
- **`state.ads` is populated at `DOMContentLoaded` via `GET /api/ads/active`** ✓ — Confirmed in `app.js`.

---

## Unverified / Wrong Assumptions

- **WRONG — Design §3: "Decorated with `@check_rate_limit(100, 3600)` ... returns `200` on over-limit"** — The actual decorator returns `429`, contradicting both the design's own error table entry and FR-5.4. See Finding 1.

- **WRONG — Design §3: "Recompute `unique_reach` ... +1 for the row we just added (not yet committed)"** — SQLAlchemy's default auto-flush will have already committed the row to the transaction before the COUNT query runs, making the `+1` a double-count. See Finding 3.

- **UNVERIFIED — Design §2: "one extra attribute access per campaign, not an extra query (relationships lazy-load on first access within the same session)"** — SQLAlchemy lazy loading does issue one additional SQL query per relationship access, not "one extra attribute access." For N campaigns each triggering two lazy loads (advertisements + placement), this is 2N additional queries. The claim that it is not an extra query is wrong. See Finding 4.

- **MISSING — Design §4: Payment creation mechanism** — The design implies `AdPayment` rows exist for the payments admin tab, but no creation point is defined anywhere. See Finding 13.

- **WRONG — Design §3: URL check `'/admin' in url.lower()`** — This is broader than FR-6.2 which requires checking for `/api/admin`, not any URL segment containing "admin." See Finding 11.

- **UNVERIFIED — Design §1: `AdvertiserSession.token` lacks `index=True`** — The design omits the index present on the analogous `AdminSession` and `AccountSession` models. See Finding 9.

- **UNVERIFIED — Design §2: `GET /api/advertiser/campaigns/<id>/report` iteration mechanism** — The day-by-day loop is described by its count only; the actual date generation code using `timedelta` is not shown. See Finding 10.
