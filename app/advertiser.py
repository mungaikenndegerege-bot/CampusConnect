import os
import uuid
import secrets
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app import db
from app.models import (Advertiser, AdvertiserSession, AdPlacement, AdCampaign,
                        Advertisement, AdDailyStat, AdPayment)
from datetime import date as _date, timedelta as _timedelta

advertiser_bp = Blueprint('advertiser_bp', __name__)


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_upload(file):
    if file and _allowed_file(file.filename):
        ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        filename = uuid.uuid4().hex + '.' + ext
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None


def require_advertiser():
    token = request.headers.get('X-Advertiser-Token')
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(days=30)
    session = AdvertiserSession.query.filter(
        AdvertiserSession.token == token,
        AdvertiserSession.created_at >= cutoff
    ).first()
    return session  # None on failure


# ---- Registration & Auth ----

@advertiser_bp.route('/api/advertiser/register', methods=['POST'])
def adv_register():
    d = request.get_json(silent=True) or {}
    business_name = (d.get('business_name') or '').strip()
    contact_name = (d.get('contact_name') or '').strip()
    email = (d.get('email') or '').strip().lower()
    password = d.get('password') or ''

    if not business_name:
        return jsonify({'error': 'business_name is required'}), 400
    if not contact_name:
        return jsonify({'error': 'contact_name is required'}), 400
    if not email or '@' not in email:
        return jsonify({'error': 'A valid email is required'}), 400
    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    if Advertiser.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    adv = Advertiser(
        business_name=business_name,
        contact_name=contact_name,
        email=email,
        phone=(d.get('phone') or '').strip() or None,
        password_hash=generate_password_hash(password),
        website=(d.get('website') or '').strip() or None,
        description=(d.get('description') or '').strip() or None,
        status='pending'
    )
    db.session.add(adv)
    db.session.commit()
    return jsonify({'advertiser': adv.to_dict()}), 201


@advertiser_bp.route('/api/advertiser/login', methods=['POST'])
def adv_login():
    d = request.get_json(silent=True) or {}
    email = (d.get('email') or '').strip().lower()
    password = d.get('password') or ''

    adv = Advertiser.query.filter_by(email=email).first()
    if not adv or not check_password_hash(adv.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = secrets.token_hex(32)
    sess = AdvertiserSession(advertiser_id=adv.id, token=token)
    db.session.add(sess)
    db.session.commit()
    return jsonify({'token': token, 'advertiser': adv.to_dict()}), 200


@advertiser_bp.route('/api/advertiser/logout', methods=['POST'])
def adv_logout():
    token = request.headers.get('X-Advertiser-Token')
    if token:
        AdvertiserSession.query.filter_by(token=token).delete()
        db.session.commit()
    return jsonify({'ok': True}), 200


@advertiser_bp.route('/api/advertiser/me', methods=['GET'])
def adv_me():
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    advertiser = adv_session.advertiser
    return jsonify(advertiser.to_dict()), 200


@advertiser_bp.route('/api/advertiser/me', methods=['PUT'])
def adv_update_me():
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    advertiser = adv_session.advertiser
    d = request.get_json(silent=True) or {}
    if 'business_name' in d:
        advertiser.business_name = (d['business_name'] or '').strip()
    if 'contact_name' in d:
        advertiser.contact_name = (d['contact_name'] or '').strip()
    if 'phone' in d:
        advertiser.phone = (d['phone'] or '').strip() or None
    if 'website' in d:
        advertiser.website = (d['website'] or '').strip() or None
    if 'description' in d:
        advertiser.description = (d['description'] or '').strip() or None
    db.session.commit()
    return jsonify(advertiser.to_dict()), 200


# ---- Placements (public) ----

@advertiser_bp.route('/api/advertiser/placements', methods=['GET'])
def adv_placements():
    placements = AdPlacement.query.filter_by(active=True).order_by(AdPlacement.price_per_day).all()
    return jsonify([p.to_dict() for p in placements]), 200


# ---- Campaigns ----

@advertiser_bp.route('/api/advertiser/campaigns', methods=['POST'])
def adv_create_campaign():
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    advertiser = adv_session.advertiser
    if advertiser.status != 'approved':
        return jsonify({'error': 'Account pending approval'}), 403

    # Accept multipart/form-data
    d = request.form if request.form else request.get_json(silent=True) or {}

    name = (d.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    start_str = d.get('start_date', '')
    end_str = d.get('end_date', '')
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    if end_date < start_date:
        return jsonify({'error': 'end_date must be on or after start_date'}), 400

    try:
        placement_id = int(d.get('placement_id', ''))
    except (ValueError, TypeError):
        return jsonify({'error': 'placement_id must be an integer'}), 400

    placement = AdPlacement.query.get(placement_id)
    if not placement or not placement.active:
        return jsonify({'error': 'Invalid or inactive placement'}), 400

    title = (d.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'title is required'}), 400

    body = (d.get('body') or '').strip() or None
    link_url = (d.get('link_url') or '').strip() or None

    image_path = None
    if 'image' in request.files:
        image_path = save_upload(request.files['image'])

    budget = placement.price_per_day * ((end_date - start_date).days + 1)

    campaign = AdCampaign(
        advertiser_id=advertiser.id,
        name=name,
        start_date=start_date,
        end_date=end_date,
        status='pending',
        total_budget=budget,
        payment_status='unpaid'
    )
    db.session.add(campaign)
    db.session.flush()  # get campaign.id

    advertisement = Advertisement(
        campaign_id=campaign.id,
        placement_id=placement_id,
        title=title,
        body=body,
        image_path=image_path,
        link_url=link_url,
        status='pending'
    )
    db.session.add(advertisement)

    # Fix 5: auto-create AdPayment row with status='pending'
    payment = AdPayment(
        campaign_id=campaign.id,
        amount=budget,
        payment_method='manual',
        status='pending'
    )
    db.session.add(payment)

    db.session.commit()
    return jsonify({'campaign': campaign.to_dict(), 'advertisement': advertisement.to_dict()}), 201


@advertiser_bp.route('/api/advertiser/campaigns', methods=['GET'])
def adv_list_campaigns():
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    advertiser = adv_session.advertiser

    # Fix 3: use joinedload to prevent N+1 queries
    campaigns = AdCampaign.query.filter_by(advertiser_id=advertiser.id).options(
        joinedload(AdCampaign.advertisements).joinedload(Advertisement.placement)
    ).order_by(AdCampaign.created_at.desc()).all()

    result = []
    for campaign in campaigns:
        d = campaign.to_dict()
        # Stats summary
        row = db.session.query(
            func.sum(AdDailyStat.impressions),
            func.sum(AdDailyStat.clicks)
        ).filter(AdDailyStat.campaign_id == campaign.id).first()
        imps = row[0] or 0
        clicks = row[1] or 0
        ctr = round(clicks / imps * 100, 2) if imps else 0.0
        d['stats_summary'] = {'impressions': imps, 'clicks': clicks, 'ctr': ctr}
        # Placement name from first advertisement
        d['placement_name'] = (
            campaign.advertisements[0].placement.name
            if campaign.advertisements and campaign.advertisements[0].placement
            else ''
        )
        result.append(d)
    return jsonify(result), 200


@advertiser_bp.route('/api/advertiser/campaigns/<int:cid>', methods=['GET'])
def adv_get_campaign(cid):
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    campaign = AdCampaign.query.get_or_404(cid)
    if campaign.advertiser_id != adv_session.advertiser_id:
        return jsonify({'error': 'Forbidden'}), 403
    d = campaign.to_dict()
    d['advertisements'] = [a.to_dict() for a in campaign.advertisements]
    return jsonify(d), 200


@advertiser_bp.route('/api/advertiser/campaigns/<int:cid>/stats', methods=['GET'])
def adv_campaign_stats(cid):
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    campaign = AdCampaign.query.get_or_404(cid)
    if campaign.advertiser_id != adv_session.advertiser_id:
        return jsonify({'error': 'Forbidden'}), 403

    stats = AdDailyStat.query.filter_by(campaign_id=cid).order_by(AdDailyStat.date).all()
    total_impressions = sum(s.impressions for s in stats)
    total_unique = sum(s.unique_reach for s in stats)
    total_clicks = sum(s.clicks for s in stats)
    ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions else 0.0

    daily = [{'date': s.date.isoformat(), 'impressions': s.impressions, 'clicks': s.clicks} for s in stats]
    return jsonify({
        'impressions': total_impressions,
        'unique_reach': total_unique,
        'clicks': total_clicks,
        'ctr': ctr,
        'daily': daily
    }), 200


@advertiser_bp.route('/api/advertiser/campaigns/<int:cid>/report', methods=['GET'])
def adv_campaign_report(cid):
    adv_session = require_advertiser()
    if not adv_session:
        return jsonify({'error': 'Unauthorized'}), 401
    campaign = AdCampaign.query.get_or_404(cid)
    if campaign.advertiser_id != adv_session.advertiser_id:
        return jsonify({'error': 'Forbidden'}), 403

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'impressions', 'unique_reach', 'clicks', 'ctr'])

    stat_map = {s.date: s for s in AdDailyStat.query.filter_by(campaign_id=cid).all()}
    days = (campaign.end_date - campaign.start_date).days + 1
    for i in range(days):
        day = campaign.start_date + _timedelta(days=i)
        s = stat_map.get(day)
        imps = s.impressions if s else 0
        reach = s.unique_reach if s else 0
        clks = s.clicks if s else 0
        ctr = round(clks / imps * 100, 2) if imps else 0.0
        writer.writerow([day.isoformat(), imps, reach, clks, ctr])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="campaign_{cid}_report.csv"'}
    )
