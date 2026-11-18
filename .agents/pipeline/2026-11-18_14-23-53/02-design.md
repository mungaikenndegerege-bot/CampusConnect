# Technical Design: CampusConnect Advertiser Dashboard and Analytics System

## Overview

The implementation adds three new Python modules (`app/advertiser.py`, `app/ad_tracking.py`, extensions appended to `app/admin.py`) and three new frontend assets (`templates/advertiser.html`, `static/css/advertiser.css`, `static/js/advertiser.js`) to the existing Flask monolith. All new SQLAlchemy models are appended to `app/models.py`. Blueprint registration and the `/advertiser` route are added to `app/__init__.py`. The seed script is extended to seed default placement records.

No existing route, model, or template is removed or renamed. The only modifications to existing files are: `app/models.py` (append-only), `app/admin.py` (append-only), `app/public.py` (single function replacement for `get_active_ads` to extend it), `app/__init__.py` (append-only inside `create_app`), `templates/admin.html` (five tab buttons appended to the `<nav class="admin-tabs">`), `static/js/admin.js` (append-only), and `static/js/app.js` (replace `renderAdBanner` and add two new functions).

**Technology stack (locked):** Python 3.11, Flask 3.0.3, Flask-SQLAlchemy 3.1.1, Flask-CORS 4.0.1, Werkzeug 3.0.3, SQLite (dev) / PostgreSQL-compatible SQLAlchemy types, stdlib `hashlib`, `csv`, `io`, `secrets`. Chart.js from CDN (`https://cdn.jsdelivr.net/npm/chart.js`). No new Python packages; `requirements.txt` is unchanged.

---

## 1. Database Models (`app/models.py`)

All eight new model classes are appended after `InstitutionPostComment`, the last existing model. The file keeps its existing `import uuid` and `from datetime import datetime`. The new models additionally need `from datetime import datetime, date` — since `datetime` is already imported, only `date` needs to be added to that import line.

### `to_dict()` convention

All new models implement `to_dict()` following the pattern established by `Institution` and `InstitutionCommunity`: a plain method returning a dict of column values with `datetime` and `date` objects serialised via `.isoformat()`. Nullable fields return `None`. SQLAlchemy relationship objects (`advertiser`, `campaign`, `placement`) are **not** eagerly included in `to_dict()` to avoid N+1 queries; routes that need them join explicitly or add a bespoke serialiser inline.

### `AdDailyStat` upsert strategy

SQLite and PostgreSQL have different upsert syntax. The design uses a fetch-then-insert-or-update pattern within a single `db.session` transaction:

1. `stat = AdDailyStat.query.filter_by(advertisement_id=ad_id, date=today).first()`
2. If found: increment the relevant counter field.
3. If not found: create a new row.
4. Single `db.session.commit()` covering both the event row and the stat update.

The `UniqueConstraint('advertisement_id', 'date', name='uq_ad_daily')` guards against concurrent inserts (two requests for the same ad in the same millisecond). In that edge case, one transaction will get a constraint error; it is caught, the session is rolled back, and the endpoint returns `200` without re-recording (the first writer already counted the event).

### `visitor_hash` computation

`hashlib.sha256((ip_address + date_string).encode()).hexdigest()[:16]`

- `ip_address`: `request.remote_addr or 'unknown'`
- `date_string`: `str(date.today())` (e.g. `'2026-11-18'`)
- Result: 16 hex characters. Resets every calendar day. Not reversible to the original IP.

### Model list (all appended to `app/models.py`)

```python
class Advertiser(db.Model):
    __tablename__ = 'advertisers'
    id            = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(200), nullable=False)
    contact_name  = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    phone         = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    website       = db.Column(db.String(200), nullable=True)
    description   = db.Column(db.Text, nullable=True)
    status        = db.Column(db.String(20), default='pending')
    approved_at   = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'business_name': self.business_name,
            'contact_name': self.contact_name, 'email': self.email,
            'phone': self.phone, 'website': self.website,
            'description': self.description, 'status': self.status,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AdvertiserSession(db.Model):
    __tablename__ = 'advertiser_sessions'
    id            = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertisers.id'))
    token         = db.Column(db.String(64), unique=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    advertiser    = db.relationship('Advertiser', backref='sessions')

    def to_dict(self):
        return {'id': self.id, 'advertiser_id': self.advertiser_id,
                'created_at': self.created_at.isoformat() if self.created_at else None}

class AdPlacement(db.Model):
    __tablename__ = 'ad_placements'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    description   = db.Column(db.Text, nullable=True)
    price_per_day = db.Column(db.Float, default=0.0)
    active        = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description,
                'price_per_day': self.price_per_day, 'active': self.active}

class AdCampaign(db.Model):
    __tablename__ = 'ad_campaigns'
    id             = db.Column(db.Integer, primary_key=True)
    advertiser_id  = db.Column(db.Integer, db.ForeignKey('advertisers.id'))
    name           = db.Column(db.String(200), nullable=False)
    start_date     = db.Column(db.Date, nullable=False)
    end_date       = db.Column(db.Date, nullable=False)
    status         = db.Column(db.String(20), default='pending')
    total_budget   = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='unpaid')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    advertiser     = db.relationship('Advertiser', backref='campaigns')

    def to_dict(self):
        return {
            'id': self.id, 'advertiser_id': self.advertiser_id,
            'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status, 'total_budget': self.total_budget,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Advertisement(db.Model):
    __tablename__ = 'advertisements'
    id           = db.Column(db.Integer, primary_key=True)
    campaign_id  = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    placement_id = db.Column(db.Integer, db.ForeignKey('ad_placements.id'))
    title        = db.Column(db.String(200), nullable=False)
    body         = db.Column(db.Text, nullable=True)
    image_path   = db.Column(db.String(300), nullable=True)
    link_url     = db.Column(db.String(500), nullable=True)
    status       = db.Column(db.String(20), default='pending')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    campaign     = db.relationship('AdCampaign', backref='advertisements')
    placement    = db.relationship('AdPlacement', backref='advertisements')

    def to_dict(self):
        return {
            'id': self.id, 'campaign_id': self.campaign_id,
            'placement_id': self.placement_id,
            'title': self.title, 'body': self.body,
            'image_path': self.image_path, 'link_url': self.link_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AdImpression(db.Model):
    __tablename__ = 'ad_impressions'
    id               = db.Column(db.Integer, primary_key=True)
    advertisement_id = db.Column(db.Integer, db.ForeignKey('advertisements.id'))
    campaign_id      = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    visitor_hash     = db.Column(db.String(64), nullable=True)
    placement        = db.Column(db.String(100), nullable=True)
    recorded_at      = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__   = (db.Index('ix_imp_ad_date', 'advertisement_id', 'recorded_at'),)

    def to_dict(self):
        return {'id': self.id, 'advertisement_id': self.advertisement_id,
                'campaign_id': self.campaign_id, 'placement': self.placement,
                'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None}

class AdClick(db.Model):
    __tablename__ = 'ad_clicks'
    id               = db.Column(db.Integer, primary_key=True)
    advertisement_id = db.Column(db.Integer, db.ForeignKey('advertisements.id'))
    campaign_id      = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    visitor_hash     = db.Column(db.String(64), nullable=True)
    placement        = db.Column(db.String(100), nullable=True)
    destination_url  = db.Column(db.String(500), nullable=True)
    recorded_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'advertisement_id': self.advertisement_id,
                'campaign_id': self.campaign_id, 'placement': self.placement,
                'destination_url': self.destination_url,
                'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None}

class AdDailyStat(db.Model):
    __tablename__ = 'ad_daily_stats'
    id               = db.Column(db.Integer, primary_key=True)
    advertisement_id = db.Column(db.Integer, db.ForeignKey('advertisements.id'))
    campaign_id      = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    date             = db.Column(db.Date, nullable=False)
    impressions      = db.Column(db.Integer, default=0)
    unique_reach     = db.Column(db.Integer, default=0)
    clicks           = db.Column(db.Integer, default=0)
    __table_args__   = (db.UniqueConstraint('advertisement_id', 'date', name='uq_ad_daily'),)

    def to_dict(self):
        return {
            'id': self.id, 'advertisement_id': self.advertisement_id,
            'campaign_id': self.campaign_id,
            'date': self.date.isoformat() if self.date else None,
            'impressions': self.impressions, 'unique_reach': self.unique_reach,
            'clicks': self.clicks
        }

class AdPayment(db.Model):
    __tablename__ = 'ad_payments'
    id             = db.Column(db.Integer, primary_key=True)
    campaign_id    = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    amount         = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    reference      = db.Column(db.String(100), nullable=True)
    status         = db.Column(db.String(20), default='pending')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at   = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 'campaign_id': self.campaign_id,
            'amount': self.amount, 'payment_method': self.payment_method,
            'reference': self.reference, 'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }
```

The `datetime` import line in `models.py` is updated from `from datetime import datetime` to `from datetime import datetime, date` to support the `db.Column(db.Date, ...)` default comparisons in route code.

---

## 2. Advertiser Blueprint (`app/advertiser.py`)

New file. Blueprint named `advertiser_bp`. Registered without URL prefix in `__init__.py`. Follows the structure of the existing `admin.py`: a guard function, a `save_upload` helper (copied from `admin.py` to avoid cross-blueprint imports), and route handlers. Auth uses `werkzeug.security.check_password_hash` / `generate_password_hash`, the same library already used by the existing `Account` model.

### Guard function

```python
def require_advertiser():
    token = request.headers.get('X-Advertiser-Token')
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(days=30)
    session = AdvertiserSession.query.filter(
        AdvertiserSession.token == token,
        AdvertiserSession.created_at >= cutoff
    ).first()
    return session   # None on failure; .advertiser_id on success
```

Returns `None` on any failure. Every protected route checks the return value and returns `401` if `None`. The function never raises, keeping error handling explicit.

### `POST /api/advertiser/register`

Input (JSON): `business_name` (required, str, 1–200), `contact_name` (required, str, 1–100), `email` (required, str, contains `@`, max 200, lowercased before storage), `password` (required, str, min 8 chars), `phone` (optional), `website` (optional), `description` (optional).

Validation failures return `400 {'error': '<field> is required'}` or `400 {'error': 'Password must be at least 8 characters'}`. Duplicate email returns `409 {'error': 'Email already registered'}`. On success, creates `Advertiser` with `status='pending'`, commits, returns `201 {'advertiser': advertiser.to_dict()}`.

### `POST /api/advertiser/login`

Input (JSON): `email` (lowercased), `password`.

Fetches `Advertiser.query.filter_by(email=email).first()`. If not found or `check_password_hash` fails: `401 {'error': 'Invalid credentials'}`. On success, generates a 64-character token using `import secrets; token = secrets.token_hex(32)` (stdlib, no new package). Creates `AdvertiserSession`, commits, returns `200 {'token': token, 'advertiser': advertiser.to_dict()}` regardless of approval status so a `pending` advertiser can log in and see their status (AC-3).

### `POST /api/advertiser/logout`

Deletes the `AdvertiserSession` row matching the `X-Advertiser-Token` header. Returns `200 {'ok': True}` even if the token was not found (idempotent).

### `GET /api/advertiser/me`

Requires `require_advertiser()`. Returns `advertiser.to_dict()` for the session owner.

### `PUT /api/advertiser/me`

Requires auth. Accepts any subset of `business_name`, `contact_name`, `phone`, `website`, `description`. Email and password are not updatable in v1. Commits and returns updated `to_dict()`.

### `GET /api/advertiser/placements`

No auth required. Returns `[p.to_dict() for p in AdPlacement.query.filter_by(active=True).order_by(AdPlacement.price_per_day).all()]`.

### `POST /api/advertiser/campaigns`

Requires auth. If `advertiser.status != 'approved'`: `403 {'error': 'Account pending approval'}`.

Accepts `multipart/form-data` (to allow image alongside fields). Fields: `name` (required), `start_date` (required, `YYYY-MM-DD`), `end_date` (required, `YYYY-MM-DD`, must be ≥ `start_date`), `placement_id` (required, integer, must reference an active `AdPlacement`), `title` (required), `body` (optional), `link_url` (optional), `image` file (optional).

Date parsing: `datetime.strptime(d, '%Y-%m-%d').date()`. Parse failure → `400 {'error': 'Invalid date format. Use YYYY-MM-DD'}`. `end_date < start_date` → `400 {'error': 'end_date must be on or after start_date'}`.

Budget: `placement.price_per_day * ((end_date - start_date).days + 1)`.

Creates `AdCampaign` (`status='pending'`, `payment_status='unpaid'`, `total_budget=budget`) and one `Advertisement` (`status='pending'`, `placement_id`, `title`, `body`, `image_path`, `link_url`). Both are added to the session in one `db.session.commit()`. Returns `201 {'campaign': campaign.to_dict(), 'advertisement': advertisement.to_dict()}`.

Image upload: uses the same `save_upload(file)` helper (copied locally). If the file is invalid or absent, `image_path = None` and the campaign is still created (non-fatal).

### `GET /api/advertiser/campaigns`

Requires auth. Queries `AdCampaign.query.filter_by(advertiser_id=session.advertiser_id).order_by(AdCampaign.created_at.desc()).all()`. For each campaign, adds a `stats_summary` dict: `{impressions, clicks, ctr}` from summing `AdDailyStat` rows. Returns list of dicts.

Stats summary query per campaign:
```python
from sqlalchemy import func
row = db.session.query(
    func.sum(AdDailyStat.impressions),
    func.sum(AdDailyStat.clicks)
).filter_by(campaign_id=campaign.id).first()
imps = row[0] or 0
clicks = row[1] or 0
ctr = round(clicks / imps * 100, 2) if imps else 0.0
```

### `GET /api/advertiser/campaigns/<id>`

Requires auth. Fetches campaign. If `campaign.advertiser_id != session.advertiser_id`: `403 {'error': 'Forbidden'}`. Returns `campaign.to_dict()` with `'advertisements': [a.to_dict() for a in campaign.advertisements]`.

### `GET /api/advertiser/campaigns/<id>/stats`

Requires auth, ownership check. Queries `AdDailyStat.query.filter_by(campaign_id=id).order_by(AdDailyStat.date).all()`. Aggregates totals. Returns:
```json
{
  "impressions": 1200,
  "unique_reach": 950,
  "clicks": 48,
  "ctr": 4.0,
  "daily": [
    {"date": "2026-11-01", "impressions": 120, "clicks": 5},
    ...
  ]
}
```
CTR = `round(total_clicks / total_impressions * 100, 2) if total_impressions else 0.0`.

### `GET /api/advertiser/campaigns/<id>/report`

Requires auth, ownership check. Builds CSV into `io.StringIO` using `csv.writer`. Columns: `date,impressions,unique_reach,clicks,ctr`. Rows: one per calendar day from `start_date` to `end_date` inclusive. For each day, looks up the matching `AdDailyStat` row (or uses zeros if none). The day-by-day loop iterates `(end_date - start_date).days + 1` times. Returns:
```python
from flask import Response
return Response(
    output.getvalue(),
    mimetype='text/csv',
    headers={'Content-Disposition': f'attachment; filename="campaign_{id}_report.csv"'}
)
```

### Error-handling table for `app/advertiser.py`

| Failure | Recoverable? | Response | Logged? |
|---|---|---|---|
| Missing required field | — | `400 {error}` | No |
| Duplicate email at registration | — | `409 {error}` | No |
| Absent/expired token | — | `401 {error}` | No |
| Account `pending` or `rejected` on campaign creation | — | `403 {error}` | No |
| Campaign not found | — | `404` (Flask `.get_or_404`) | No |
| Campaign belongs to different advertiser | — | `403 {error}` | No |
| Invalid date string | — | `400 {error}` | No |
| `end_date` before `start_date` | — | `400 {error}` | No |
| Placement not found or inactive | — | `400 {error}` | No |
| Image upload fails (bad extension/size) | Yes — campaign created without image | `image_path=None`, request continues | No |
| DB integrity error (duplicate constraint) | Fatal for the request | `500` via Flask default | Yes (Flask stderr) |

---

## 3. Ad Tracking Blueprint (`app/ad_tracking.py`)

New file. Blueprint named `tracking_bp`. Registered without URL prefix. Imports: `hashlib`, `datetime`, `date`, `time` from stdlib; `db`, `Advertisement`, `AdCampaign`, `AdImpression`, `AdClick`, `AdDailyStat` from app models; `check_rate_limit` from `app.ratelimit`.

### `POST /api/track/impression`

Decorated with `@check_rate_limit(100, 3600)` (100 events per IP per hour). The rate-limit decorator returns `429` on over-limit. Because the decorator fires before the function body, bot detection runs inside the function body after the rate-limit check. This is acceptable: a bot hitting the rate limit silently stops being processed. Legitimate browsers will not reach 100 impressions/hour.

Execution inside the function:

1. **Bot detection:** `ua = request.headers.get('User-Agent', '').lower()`. If any of `['googlebot', 'bingbot', 'facebookexternalhit', 'python-requests', 'curl', 'wget', 'headless']` appears as a substring: return `200 {'ok': True}` without recording.
2. **Parse body:** `d = request.get_json(silent=True) or {}`. `advertisement_id = d.get('advertisement_id')`. If missing or not an integer: return `200 {'ok': True}`.
3. **Validate advertisement:** `ad = Advertisement.query.get(advertisement_id)`. If `None` or `ad.status != 'active'`: return `200 {'ok': True}`.
4. **Campaign date range:** `today = date.today()`. If `not (ad.campaign.start_date <= today <= ad.campaign.end_date)`: return `200 {'ok': True}`.
5. **Deduplication:** `visitor_hash = _make_visitor_hash(request.remote_addr)`. `today_midnight = datetime.combine(today, time.min)`. Query `AdImpression.query.filter_by(advertisement_id=advertisement_id, visitor_hash=visitor_hash).filter(AdImpression.recorded_at >= today_midnight).first()`. If found: return `200 {'ok': True}`.
6. **Record impression:** `imp = AdImpression(advertisement_id=advertisement_id, campaign_id=ad.campaign_id, visitor_hash=visitor_hash, placement=d.get('placement',''), recorded_at=datetime.utcnow())`. `db.session.add(imp)`.
7. **Upsert `AdDailyStat`:** `stat = AdDailyStat.query.filter_by(advertisement_id=advertisement_id, date=today).first()`. If found: `stat.impressions += 1`. Recompute `unique_reach`:
   ```python
   stat.unique_reach = db.session.query(
       db.func.count(db.func.distinct(AdImpression.visitor_hash))
   ).filter(
       AdImpression.advertisement_id == advertisement_id,
       AdImpression.recorded_at >= today_midnight
   ).scalar() or 0
   # +1 for the row we just added (not yet committed)
   stat.unique_reach += 1
   ```
   If not found: `stat = AdDailyStat(advertisement_id=advertisement_id, campaign_id=ad.campaign_id, date=today, impressions=1, unique_reach=1, clicks=0)`. `db.session.add(stat)`.
8. **Commit:** `db.session.commit()`. On `SQLAlchemyError`: rollback, return `200 {'ok': True}` (silent — tracking failure must not break page load).
9. Return `200 {'ok': True}`.

The `_make_visitor_hash` helper:
```python
import hashlib
from datetime import date

def _make_visitor_hash(ip):
    raw = (ip or 'unknown') + str(date.today())
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### `POST /api/track/click/<int:ad_id>`

No rate-limit decorator on the click endpoint (a user legitimately clicks many different ads). Bot detection check is applied with the same string-match logic as impressions.

Execution:
1. **Bot detection:** same UA check as impressions. If bot: return `200 {'ok': True}`.
2. **Fetch ad:** `ad = Advertisement.query.get(ad_id)`. If `None`: `404`.
3. **URL validation:** `url = ad.link_url or ''`. If not (`url.startswith('http://') or url.startswith('https://')`): return `400 {'error': 'Invalid destination URL'}`. If `'/admin'` in `url.lower()`: return `400 {'error': 'Invalid destination URL'}`.
4. **Parse optional placement:** `d = request.get_json(silent=True) or {}`. `placement = d.get('placement', '')`.
5. **visitor_hash:** `_make_visitor_hash(request.remote_addr)`.
6. **Record click:** `click = AdClick(advertisement_id=ad_id, campaign_id=ad.campaign_id, visitor_hash=vh, placement=placement, destination_url=url, recorded_at=datetime.utcnow())`. `db.session.add(click)`.
7. **Upsert `AdDailyStat.clicks`:** Same fetch-or-create pattern. `stat.clicks += 1`.
8. `db.session.commit()`. On error: rollback, still return the redirect URL (tracking failure must not break the user's click).
9. Return `200 {'redirect_url': url}`.

### Error-handling table for `app/ad_tracking.py`

| Failure | Response | Notes |
|---|---|---|
| Rate limit exceeded | `429` (from decorator) | Legitimate browsers won't hit this |
| Bot UA detected | `200 {'ok': True}` | Silent drop |
| Missing/invalid `advertisement_id` | `200 {'ok': True}` | Silent |
| Advertisement not found or inactive | `200 {'ok': True}` | Silent |
| Campaign date range exceeded | `200 {'ok': True}` | Silent |
| Duplicate impression today | `200 {'ok': True}` | Silent |
| Click on ad with no/invalid URL | `400 {error}` | Returned to frontend |
| Ad not found on click | `404` | Frontend handles |
| DB error on impression | `200 {'ok': True}` after rollback | Tracking failure is non-fatal |
| DB error on click | `200 {'redirect_url'}` after rollback | Click redirect still works |

### Extension to `GET /api/ads/active` (in `app/public.py`)

The existing three-line `get_active_ads` function is replaced. The route decorator, function name, and return type are preserved; only the body expands. The existing `ad_to_dict` local function is left unchanged.

New body:
```python
@public_bp.route('/api/ads/active')
def get_active_ads():
    from datetime import date as _date
    from app.models import Advertisement, AdCampaign
    today = _date.today()
    # Legacy Ad records — unchanged
    legacy = []
    for a in Ad.query.filter_by(active=True).order_by(Ad.created_at.desc()).all():
        d = ad_to_dict(a)
        d['ad_type'] = 'legacy'
        legacy.append(d)
    # Campaign Advertisement records
    active_adverts = (
        Advertisement.query
        .join(AdCampaign, Advertisement.campaign_id == AdCampaign.id)
        .filter(
            Advertisement.status == 'active',
            AdCampaign.start_date <= today,
            AdCampaign.end_date >= today
        )
        .all()
    )
    campaign_ads = []
    for a in active_adverts:
        campaign_ads.append({
            'id': a.id,
            'title': a.title,
            'body': a.body or '',
            'image_path': a.image_path,
            'link_url': a.link_url or '',
            'active': True,
            'click_count': 0,
            'created_at': a.created_at.isoformat(),
            'type': 'ad',
            'ad_type': 'campaign',
        })
    return jsonify(legacy + campaign_ads)
```

The `click_count: 0` field satisfies `renderAdBanner` which renders it as an unused field, maintaining the shape expected by the frontend. The local imports avoid adding `Advertisement` and `AdCampaign` to the top-level imports in `public.py` (keeping the diff minimal and preventing confusion with the legacy `Ad` model import).

---

## 4. Admin Blueprint Extensions (`app/admin.py`)

New route handlers are appended after the last existing route (`resolve_report`). The import block at the top of `admin.py` gains one line:

```python
from app.models import (Ad, Announcement, Post, MarketplaceItem, LostFoundItem,
                        AdminSession, Report,
                        Advertiser, AdCampaign, Advertisement, AdPlacement, AdPayment, AdDailyStat)
```

All new routes reuse the existing `require_admin()` guard and return `401` if it returns `None`.

### Advertiser management

```
GET /api/admin/advertisers
```
`Advertiser.query.order_by(Advertiser.created_at.desc()).all()`. Returns list of `to_dict()`.

```
PUT /api/admin/advertisers/<id>/approve
```
Fetches advertiser, sets `status='approved'`, `approved_at=datetime.utcnow()`, commits, returns `200 {'ok': True}`.

```
PUT /api/admin/advertisers/<id>/reject
```
Sets `status='rejected'`, commits, returns `200 {'ok': True}`.

### Campaign management

```
GET /api/admin/campaigns
```
`AdCampaign.query.order_by(AdCampaign.created_at.desc()).all()`. Each dict includes `advertiser_name: campaign.advertiser.business_name` for display.

```
PUT /api/admin/campaigns/<id>/approve
PUT /api/admin/campaigns/<id>/reject
PUT /api/admin/campaigns/<id>/pause
PUT /api/admin/campaigns/<id>/activate
```
Each route sets `campaign.status` to the target value and cascades to all associated `Advertisement` rows:
```python
Advertisement.query.filter_by(campaign_id=id).update({'status': new_status})
db.session.commit()
```

### Placement management

```
GET /api/admin/placements
```
`AdPlacement.query.order_by(AdPlacement.name).all()`.

```
POST /api/admin/placements
```
Input (JSON): `name` (required), `description`, `price_per_day` (required, non-negative float), `active` (bool, default `True`). Validation: `name` missing → `400`. `price_per_day < 0` → `400`. Creates and returns `201`.

```
PUT /api/admin/placements/<id>
```
Updates any subset of `name`, `description`, `price_per_day`, `active`. Returns updated `to_dict()`.

### Revenue and payments

```
GET /api/admin/revenue
```
Returns:
```python
{
  'total_campaigns': AdCampaign.query.count(),
  'confirmed_revenue': db.session.query(db.func.sum(AdPayment.amount))
                         .filter_by(status='confirmed').scalar() or 0.0,
  'unpaid_campaigns': AdCampaign.query.filter_by(payment_status='unpaid').count(),
  'paid_campaigns': AdCampaign.query.filter_by(payment_status='paid').count(),
}
```

```
GET /api/admin/payments
```
`AdPayment.query.order_by(AdPayment.created_at.desc()).all()`. Each dict includes `campaign_name` via join.

```
PUT /api/admin/payments/<id>/confirm
```
Sets `payment.status='confirmed'`, `payment.confirmed_at=datetime.utcnow()`. Commits, returns `200 {'ok': True}`.

---

## 5. `app/__init__.py` Changes

Inside `create_app()`, append after the existing blueprint registrations:

```python
from app.advertiser import advertiser_bp
app.register_blueprint(advertiser_bp)

from app.ad_tracking import tracking_bp
app.register_blueprint(tracking_bp)

@app.route('/advertiser')
@app.route('/advertiser/')
def advertiser_portal():
    return render_template('advertiser.html')
```

Both blueprint imports are local to `create_app` (matching the existing pattern for `institutions_bp`), avoiding module-level circular imports.

---

## 6. `seed.py` Changes

Append after `seed_institutions()`:

```python
from app.models import AdPlacement
_placements = [
    {'name': 'Feed Banner',           'description': 'Appears every 5 posts in the main feed',   'price_per_day': 500.0},
    {'name': 'Institution Community', 'description': 'Appears in institution community feeds',    'price_per_day': 300.0},
    {'name': 'Homepage Top',          'description': 'Top banner on homepage',                   'price_per_day': 800.0},
    {'name': 'Sidebar',               'description': 'Sidebar placement on desktop',             'price_per_day': 200.0},
]
for _p in _placements:
    if not AdPlacement.query.filter_by(name=_p['name']).first():
        db.session.add(AdPlacement(**_p))
db.session.commit()
print('Ad placements seeded.')
```

The `filter_by(name=).first()` guard makes the block idempotent (AC-32).

---

## 7. `templates/advertiser.html`

New file. Minimal shell page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CampusConnect Advertiser Portal</title>
  <link rel="stylesheet" href="/static/css/advertiser.css">
</head>
<body>
  <header class="adv-header">
    <div class="adv-logo">CampusConnect <span>Advertiser Portal</span></div>
    <div id="adv-user-bar"></div>
  </header>
  <main id="adv-app"></main>
  <script src="/static/js/advertiser.js"></script>
</body>
</html>
```

---

## 8. `static/css/advertiser.css`

All rules are prefixed with `.adv-*` class selectors or scoped to the `body` of the advertiser page to prevent style leakage into `index.html` or `admin.html`. Those two pages load only `style.css`, not `advertiser.css`, so there is no cross-contamination risk; the prefix is a belt-and-suspenders measure.

Key design decisions:

- **Colour tokens:** `:root { --adv-primary: #6C3CE1; --adv-accent: #F5A623; --adv-bg: #f8f9fa; }`. Using CSS custom properties means a single change updates all usages.
- **Layout:** `.adv-layout` uses `display: grid; grid-template-columns: 220px 1fr` at `min-width: 769px`. Below that breakpoint, switches to `grid-template-columns: 1fr` with `.adv-sidebar` becoming a horizontal tab strip (`display: flex; overflow-x: auto`).
- **Stat cards:** `.adv-stat-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }`. Each `.adv-stat-card` has a large `font-size: 2rem` number and a small label.
- **Status badges:** `.badge-pending { background: #fff3e0; color: #e65100; }`, `.badge-approved { background: #e3f2fd; color: #1565c0; }`, `.badge-active { background: #e8f5e9; color: #2e7d32; }`, `.badge-paused { background: #f5f5f5; color: #616161; }`, `.badge-rejected { background: #ffebee; color: #c62828; }`, `.badge-completed { background: #ede7f6; color: #4527a0; }`.
- **Chart container:** `.adv-chart-container { position: relative; height: 300px; width: 100%; }`.
- **Tables:** `.adv-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }` with alternating row colours.
- **Forms:** `.adv-form-group`, `.adv-input`, `.adv-btn` classes with consistent padding, border-radius `8px`, and transition effects.

---

## 9. `static/js/advertiser.js`

A self-contained SPA. No dependency on `app.js`, `admin.js`, or `feed.js`. Token stored in `localStorage` under key `cc_adv_token`.

### Module-level state

```javascript
const ADV_TOKEN_KEY = 'cc_adv_token';
let _currentAdvertiser = null;
let _currentCampaignId = null;
let _chartjsLoaded = false;
let _chartInstance = null;
```

### API helper

```javascript
async function advApi(method, path, body, isFormData) {
  const opts = { method, headers: { 'X-Advertiser-Token': localStorage.getItem(ADV_TOKEN_KEY) || '' } };
  if (body && !isFormData) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  else if (body && isFormData) { opts.body = body; }
  const res = await fetch(path, opts);
  if (!res.ok) throw { status: res.status, data: await res.json().catch(() => ({})) };
  return res.json();
}
```

Identical structure to `adminApi` in `admin.js` with header name changed.

### Screen router

```javascript
function renderScreen(name, param) {
  _currentScreen = name;
  const app = document.getElementById('adv-app');
  const screens = { login: renderLoginScreen, dashboard: renderDashboard,
                    campaigns: renderCampaignList, 'new-campaign': renderNewCampaign,
                    'campaign-detail': renderCampaignDetail, settings: renderSettings };
  if (screens[name]) screens[name](param);
}
```

`DOMContentLoaded` checks `localStorage.getItem(ADV_TOKEN_KEY)`. If present, attempts `GET /api/advertiser/me`; on `401`, clears token and shows login; on success, sets `_currentAdvertiser` and shows dashboard.

### Login/Register screen

Two forms within the same screen toggled by clicking "Register" / "Back to Login" links. Login calls `POST /api/advertiser/login`; on success, stores token and renders dashboard. Register calls `POST /api/advertiser/register`; on `201`, automatically logs in (calls login with same credentials). Errors display in an inline `<p class="adv-error">` element.

### Dashboard screen

Fetches `GET /api/advertiser/campaigns` in parallel with `GET /api/advertiser/me`. Sums totals across all campaigns to populate stat cards (Total Impressions, Total Clicks, Overall CTR, Active Campaign Count). Renders a table of the 5 most recent campaigns. Sidebar/tab nav links to other screens.

### Campaign list screen

Fetches `GET /api/advertiser/campaigns`. Renders a full table with columns: Name, Status badge, Placement (looked up from `advertisement.placement_id` — the campaign dict includes the advertisement list from the detail route, but the list route returns a summary; the placement name is included in the campaign dict via a `placement_name` field that the backend adds to the campaign list serialiser). Columns: Name, Dates, Status, Impressions, Clicks, CTR, [View] button.

**Backend addition for campaign list serialiser:** In `GET /api/advertiser/campaigns`, each campaign dict includes `'placement_name'` by querying the first advertisement's placement: `campaign.advertisements[0].placement.name if campaign.advertisements else ''`. This is loaded via SQLAlchemy relationship and is one extra attribute access per campaign, not an extra query (relationships lazy-load on first access within the same session).

### New Campaign form screen

Fetches `GET /api/advertiser/placements` to populate the placement `<select>`. Submits as `multipart/form-data`. On `201`, calls `renderScreen('campaigns')`. Validation of required fields is done client-side before submit (empty-string check on `name`, `start_date`, `end_date`, `placement_id`, `title`) with inline error messages; server-side validation is the authoritative gate.

### Campaign Detail screen

Fetches `GET /api/advertiser/campaigns/<id>` and `GET /api/advertiser/campaigns/<id>/stats` concurrently via `Promise.all`. Renders stat cards for the individual campaign. Renders Chart.js line chart:

Chart.js loading strategy: on first call to `renderCampaignDetail`, if `!_chartjsLoaded`, create a `<script>` tag pointing to `https://cdn.jsdelivr.net/npm/chart.js`, append to `<head>`, and set `script.onload = () => { _chartjsLoaded = true; _drawChart(stats.daily); }`. On subsequent calls (chart already loaded), call `_drawChart` directly.

```javascript
function _drawChart(daily) {
  if (_chartInstance) { _chartInstance.destroy(); _chartInstance = null; }
  const ctx = document.getElementById('adv-chart').getContext('2d');
  _chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: daily.map(d => d.date),
      datasets: [
        { label: 'Impressions', data: daily.map(d => d.impressions),
          borderColor: '#6C3CE1', backgroundColor: 'rgba(108,60,225,0.08)', tension: 0.3 },
        { label: 'Clicks', data: daily.map(d => d.clicks),
          borderColor: '#F5A623', backgroundColor: 'rgba(245,166,35,0.08)', tension: 0.3 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
}
```

The `_chartInstance.destroy()` call prevents Chart.js canvas reuse errors when navigating away and back.

CSV download: `<a href="/api/advertiser/campaigns/${id}/report" download class="adv-btn">Download CSV</a>`. No JavaScript needed; `Content-Disposition: attachment` triggers the browser download.

### Settings screen

Pre-fills form from `_currentAdvertiser`. Submits via `PUT /api/advertiser/me`. On success, updates `_currentAdvertiser` and shows a success message.

### Logout

Clears `localStorage.removeItem(ADV_TOKEN_KEY)`, calls `POST /api/advertiser/logout`, renders login screen.

---

## 10. `static/js/app.js` Modifications

Two targeted changes:

### Replace `renderAdBanner`

```javascript
const _adImpressionsSeen = new Set(); // module-level, reset on page load

function renderAdBanner(ad) {
  const adType = ad.ad_type || 'legacy';
  const clickFn = adType === 'campaign'
    ? `advTrackClick(${ad.id}, event)`
    : `fetch('/api/ads/${ad.id}/click',{method:'POST'})`;
  return `<div class="ad-banner" data-ad-id="${ad.id}" data-ad-type="${adType}">
    <div class="ad-label">Sponsored</div>
    ${ad.image_path ? `<img class="ad-image" src="/api/uploads/${escHtml(ad.image_path)}" alt="">` : ''}
    <div class="ad-title">${escHtml(ad.title)}</div>
    <div class="ad-body">${escHtml(ad.body)}</div>
    ${ad.link_url ? `<a class="ad-link" href="${escHtml(ad.link_url)}" target="_blank" rel="noopener" onclick="${clickFn}">Learn More</a>` : ''}
  </div>`;
}
```

For `ad_type === 'legacy'`, the `onclick` is identical to the original (`fetch('/api/ads/${ad.id}/click',{method:'POST'})`), so legacy ads are unaffected.

### Add `observeAdImpression` and `advTrackClick` after `renderAdBanner`

```javascript
function observeAdImpression(adId, placement) {
  const el = document.querySelector(`[data-ad-id="${adId}"]`);
  if (!el || _adImpressionsSeen.has(adId)) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && entry.intersectionRatio >= 0.5 && !_adImpressionsSeen.has(adId)) {
        const timer = setTimeout(() => {
          if (!document.querySelector(`[data-ad-id="${adId}"]`)) return; // element removed
          _adImpressionsSeen.add(adId);
          fetch('/api/track/impression', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ advertisement_id: adId, placement: placement || '' })
          }).catch(() => {});
          observer.disconnect();
        }, 1000);
        // If the element leaves view before 1s, cancel the timer
        entry._timer = timer;
      } else if (!entry.isIntersecting && entry._timer) {
        clearTimeout(entry._timer);
      }
    });
  }, { threshold: 0.5 });
  observer.observe(el);
}

function advTrackClick(adId, event) {
  if (event) event.preventDefault();
  fetch(`/api/track/click/${adId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ placement: '' })
  })
    .then(r => r.json())
    .then(data => { if (data.redirect_url) window.open(data.redirect_url, '_blank'); })
    .catch(() => {});
}
```

**Where `observeAdImpression` is called:** The `injectAds` function inserts ad objects into the feed array. After the feed renders its HTML into the DOM, the render function (in `feed.js`, which calls `renderAdBanner`) must call `observeAdImpression`. The call site is in `feed.js`'s `renderFeed` function, after the feed HTML is inserted into the DOM. Because `feed.js` is not in scope for this design to modify directly, the design adds `observeAdImpression` calls by hooking into the `injectAds` function: after returning the items array, `injectAds` stores the ad IDs for later observation, and a `MutationObserver` on the feed container triggers `observeAdImpression` for each `[data-ad-id]` element that enters the DOM.

**Alternative approach (simpler, chosen):** Add a `setTimeout(() => { ... }, 100)` call at the end of `injectAds` that iterates over injected ad IDs and calls `observeAdImpression`. This avoids `MutationObserver` complexity:

```javascript
function injectAds(items) {
  if (!state.ads.length) return items;
  const result = [];
  const injectedAdIds = [];
  items.forEach((item, i) => {
    result.push(item);
    if ((i + 1) % 5 === 0) {
      const ad = state.ads[state.adIndex % state.ads.length];
      state.adIndex++;
      result.push({ ...ad, type: 'ad' });
      if (ad.ad_type === 'campaign') injectedAdIds.push(ad.id);
    }
  });
  if (injectedAdIds.length) {
    setTimeout(() => {
      injectedAdIds.forEach(id => observeAdImpression(id, 'feed'));
    }, 100);
  }
  return result;
}
```

The 100 ms delay gives the feed renderer time to insert the HTML into the DOM before `observeAdImpression` queries for `[data-ad-id]`.

---

## 11. `templates/admin.html` Changes

Five `<button>` elements are appended inside the existing `<nav class="admin-tabs">`:

```html
<button class="admin-tab-btn" data-tab="advertisers">Advertisers</button>
<button class="admin-tab-btn" data-tab="adcampaigns">Campaigns</button>
<button class="admin-tab-btn" data-tab="placements">Placements</button>
<button class="admin-tab-btn" data-tab="revenue">Revenue</button>
<button class="admin-tab-btn" data-tab="payments">Payments</button>
```

Tab names `advertisers`, `adcampaigns`, `placements`, `revenue`, `payments` are chosen to avoid collisions with existing tab names (`ads`, `announcements`, `posts`, `marketplace`, `lostandfound`, `reports`, `institutions`). The tab name `adcampaigns` (not `campaigns`) is used because it avoids any future collision with a hypothetical `campaigns` tab in a different context.

---

## 12. `static/js/admin.js` Extensions

Five `loadXxxTab()` functions and their action helpers are appended to the existing file. The existing `loadTab` function's `loaders` object is extended to include the five new keys. This requires a one-line change in `loadTab`:

```javascript
// Existing line (replace):
const loaders = { ads: loadAdsTab, announcements: loadAnnouncementsTab, posts: loadPostsTab, marketplace: loadMarketplaceTab, lostandfound: loadLFTab, reports: loadReportsTab, institutions: loadInstitutionsAdminTab };

// Replacement:
const loaders = { ads: loadAdsTab, announcements: loadAnnouncementsTab, posts: loadPostsTab, marketplace: loadMarketplaceTab, lostandfound: loadLFTab, reports: loadReportsTab, institutions: loadInstitutionsAdminTab,
  advertisers: loadAdvertisersTab, adcampaigns: loadAdCampaignsTab, placements: loadPlacementsTab, revenue: loadRevenueTab, payments: loadPaymentsTab };
```

### `loadAdvertisersTab()`

Fetches `GET /api/admin/advertisers`. Renders a table: Business Name, Contact, Email, Status badge, Created, Actions (Approve / Reject). Approve calls `PUT /api/admin/advertisers/<id>/approve`; Reject calls `PUT /api/admin/advertisers/<id>/reject`. After each action, reloads the tab.

### `loadAdCampaignsTab()`

Fetches `GET /api/admin/campaigns`. Renders a table: Campaign Name, Advertiser, Dates, Status badge, Budget (KSh), Actions (Approve / Reject / Pause / Activate — buttons shown conditionally based on current status). After each action, reloads the tab.

### `loadPlacementsTab()`

Fetches `GET /api/admin/placements`. Renders a create form (name, description, price_per_day, active checkbox) and a list of existing placements with Edit button. Edit opens the existing `openModal()` with an edit form that submits to `PUT /api/admin/placements/<id>`.

### `loadRevenueTab()`

Fetches `GET /api/admin/revenue`. Renders four stat cards: Total Campaigns, Confirmed Revenue (KSh), Unpaid Campaigns, Paid Campaigns. No table; this is a summary-only view.

### `loadPaymentsTab()`

Fetches `GET /api/admin/payments`. Renders a table: Payment ID, Campaign, Amount, Method, Reference, Status badge, Created, Actions (Confirm button for `pending` payments). Confirm calls `PUT /api/admin/payments/<id>/confirm`.

---

## 13. Edge Cases

**`injectAds` with zero ads:** `if (!state.ads.length) return items` — unchanged from existing code. Campaign ads mix seamlessly into `state.ads` because `GET /api/ads/active` returns a combined array; the frontend needs no changes to the array source.

**`AdDailyStat` unique constraint race:** Two simultaneous impression requests for the same ad from different IPs on the same day can both pass the dedup check (different `visitor_hash`) and both attempt to insert `AdDailyStat`. One will get a `UNIQUE constraint failed` error. The design wraps the commit in a `try/except SQLAlchemyError` block, rolls back on failure, and returns `200` anyway. The impression event itself (`AdImpression`) may be lost in the loser transaction, but this is an acceptable edge case for analytics (not financial data).

**Campaign ads in `get_active_ads` when no campaigns exist:** The `.join(AdCampaign, ...)` query returns an empty list; the function returns only legacy ads. No crash.

**`advertisement_id` in tracking that belongs to a legacy `Ad`:** The `AdImpression` and `AdClick` endpoints only accept IDs from the `advertisements` table (new model). There is no cross-table ID confusion because the two tables have independent auto-increment sequences starting from 1; a legacy `Ad.id = 5` and an `Advertisement.id = 5` can coexist, but the tracking endpoints query only `Advertisement`. The frontend distinguishes the two via `ad_type` and only calls tracking endpoints for `ad_type === 'campaign'`.

**`Chart.js` CDN unavailable:** The `script.onload` event fires only if the CDN responds. If it fails, the chart container stays empty. The stat cards above the chart still render from the API data. This is acceptable for a first version; a future hardening step would bundle Chart.js.

**`observeAdImpression` called before DOM insert:** The 100 ms `setTimeout` in `injectAds` mitigates the race condition between the array being prepared and the DOM being rendered. If rendering takes longer (e.g. slow device), `observeAdImpression` calls `querySelector` and finds nothing, returning silently. The `IntersectionObserver` is simply never registered for that ad; no impression is recorded. This is an under-count edge case, not a double-count.

**Advertiser sees `click_count: 0` on their campaign ads:** The `click_count` field in the unified `get_active_ads` response is a legacy field for the old `Ad` model. Campaign ads carry `0` and the frontend renders nothing for it (the existing `renderAdBanner` does not display `click_count`). Real click data for campaign ads is in `AdDailyStat.clicks` and surfaced via the analytics API.

---

## 14. Testability

**Unit-testable in isolation:**
- `_make_visitor_hash(ip)` — pure function, deterministic given a fixed date.
- `ad_to_dict` and all `to_dict()` methods — pure given a model instance.
- Budget calculation in campaign creation — `price_per_day * days`.
- CTR calculation — `round(clicks/impressions*100, 2) if impressions else 0.0`.
- URL validation logic in click tracking.
- Bot UA detection string matching.

**Integration-testable with a test Flask app + in-memory SQLite:**
- All `app/advertiser.py` routes (register, login, campaign CRUD, stats, CSV).
- All `app/ad_tracking.py` routes (impression dedup, bot filter, click validation).
- `GET /api/ads/active` unified response.
- Admin advertiser/campaign/payment routes.
- Seed script idempotency.

**Browser/manual testing (not automatable in unit tests):**
- `IntersectionObserver` behaviour (requires a real viewport).
- Chart.js CDN load and canvas rendering.
- CSV file download via `Content-Disposition` header.
- `localStorage` token persistence across page reloads.

The tracking endpoints accept only `advertisement_id` from the request body (not `visitor_hash` or `visitor_ip`), so they cannot be manipulated from the browser to fake a specific visitor identity. The dedup check is entirely server-side.

---

## 15. File Modification Summary

| File | Change type | Description |
|---|---|---|
| `app/models.py` | Append | 8 new model classes; update `datetime` import |
| `app/advertiser.py` | New | Advertiser auth and campaign routes |
| `app/ad_tracking.py` | New | Impression/click tracking endpoints |
| `app/admin.py` | Append | 12 new admin routes; update import line |
| `app/public.py` | Replace one function | Extend `get_active_ads` to include campaign ads |
| `app/__init__.py` | Append | Register 2 new blueprints; add `/advertiser` route |
| `seed.py` | Append | Seed 4 default placement records |
| `templates/advertiser.html` | New | Advertiser portal HTML shell |
| `static/css/advertiser.css` | New | Dashboard styles |
| `static/js/advertiser.js` | New | Advertiser SPA |
| `templates/admin.html` | Append 5 buttons | New tab buttons in `<nav class="admin-tabs">` |
| `static/js/admin.js` | Append + 1 line edit | 5 new tab loaders; extend `loaders` object in `loadTab` |
| `static/js/app.js` | Replace 1 function + append 2 | `renderAdBanner`, `observeAdImpression`, `advTrackClick`, `injectAds` |
| `requirements.txt` | No change | All needed libraries already present |
| `Dockerfile` | No change | `python seed.py` already in build command |
| `config.py` | No change | No new config keys required |
