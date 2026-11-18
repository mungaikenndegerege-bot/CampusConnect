import hashlib
import threading
from datetime import datetime, date, time
from collections import defaultdict
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import Advertisement, AdImpression, AdClick, AdDailyStat

tracking_bp = Blueprint('tracking_bp', __name__)

# In-memory rate-limit state for impression endpoint (Fix 1 & 2: inline, silent 200 drop)
_imp_hits = defaultdict(list)
_imp_lock = threading.Lock()

_BOT_AGENTS = ['googlebot', 'bingbot', 'facebookexternalhit', 'python-requests',
               'curl', 'wget', 'headless']


def _make_visitor_hash(ip):
    raw = (ip or 'unknown') + str(date.today())
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_bot(user_agent):
    ua = (user_agent or '').lower()
    return any(bot in ua for bot in _BOT_AGENTS)


@tracking_bp.route('/api/track/impression', methods=['POST'])
def track_impression():
    # Fix 1: inline rate-limit — silent 200 drop, never 429
    ip = request.remote_addr or 'unknown'
    now = datetime.utcnow().timestamp()
    with _imp_lock:
        _imp_hits[ip] = [t for t in _imp_hits[ip] if now - t < 3600]
        if len(_imp_hits[ip]) >= 100:
            return jsonify({'ok': True}), 200
        _imp_hits[ip].append(now)

    # Bot detection
    if _is_bot(request.headers.get('User-Agent', '')):
        return jsonify({'ok': True}), 200

    d = request.get_json(silent=True) or {}
    advertisement_id = d.get('advertisement_id')
    if not advertisement_id or not isinstance(advertisement_id, int):
        return jsonify({'ok': True}), 200

    ad = Advertisement.query.get(advertisement_id)
    if not ad or ad.status != 'active':
        return jsonify({'ok': True}), 200

    today = date.today()
    # Campaign date range check
    if not (ad.campaign.start_date <= today <= ad.campaign.end_date):
        return jsonify({'ok': True}), 200

    visitor_hash = _make_visitor_hash(ip)
    today_midnight = datetime.combine(today, time.min)

    # Deduplication: same ad + same visitor today
    existing_imp = AdImpression.query.filter_by(
        advertisement_id=advertisement_id,
        visitor_hash=visitor_hash
    ).filter(AdImpression.recorded_at >= today_midnight).first()
    if existing_imp:
        return jsonify({'ok': True}), 200

    try:
        # Record impression
        imp = AdImpression(
            advertisement_id=advertisement_id,
            campaign_id=ad.campaign_id,
            visitor_hash=visitor_hash,
            placement=d.get('placement', ''),
            recorded_at=datetime.utcnow()
        )
        db.session.add(imp)
        db.session.flush()  # make row visible for the unique_reach count

        # Fix 2: upsert AdDailyStat with correct unique_reach via fresh query
        existing_stat = AdDailyStat.query.filter_by(advertisement_id=advertisement_id, date=today).first()
        if not existing_stat:
            existing_stat = AdDailyStat(
                advertisement_id=advertisement_id,
                campaign_id=ad.campaign_id,
                date=today,
                impressions=0,
                unique_reach=0,
                clicks=0
            )
            db.session.add(existing_stat)
            db.session.flush()

        existing_stat.impressions += 1
        # Count unique visitors for today using a fresh query (flush already made new row visible)
        unique_count = db.session.query(
            db.func.count(db.func.distinct(AdImpression.visitor_hash))
        ).filter(
            AdImpression.advertisement_id == advertisement_id,
            AdImpression.recorded_at >= today_midnight
        ).scalar() or 0
        existing_stat.unique_reach = unique_count

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()

    return jsonify({'ok': True}), 200


@tracking_bp.route('/api/track/click/<int:ad_id>', methods=['POST'])
def track_click(ad_id):
    # Bot detection
    if _is_bot(request.headers.get('User-Agent', '')):
        return jsonify({'ok': True}), 200

    ad = Advertisement.query.get(ad_id)
    if not ad:
        return jsonify({'error': 'Not found'}), 404

    url = ad.link_url or ''
    if not (url.startswith('http://') or url.startswith('https://')):
        return jsonify({'error': 'Invalid destination URL'}), 400
    # Fix 11: use precise string from FR-6.2
    if '/api/admin' in url.lower():
        return jsonify({'error': 'Invalid destination URL'}), 400

    d = request.get_json(silent=True) or {}
    placement = d.get('placement', '')
    visitor_hash = _make_visitor_hash(request.remote_addr or 'unknown')
    today = date.today()

    try:
        click = AdClick(
            advertisement_id=ad_id,
            campaign_id=ad.campaign_id,
            visitor_hash=visitor_hash,
            placement=placement,
            destination_url=url,
            recorded_at=datetime.utcnow()
        )
        db.session.add(click)

        # Upsert AdDailyStat.clicks
        stat = AdDailyStat.query.filter_by(advertisement_id=ad_id, date=today).first()
        if not stat:
            stat = AdDailyStat(
                advertisement_id=ad_id,
                campaign_id=ad.campaign_id,
                date=today,
                impressions=0,
                unique_reach=0,
                clicks=0
            )
            db.session.add(stat)
        stat.clicks += 1
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()

    return jsonify({'redirect_url': url}), 200
