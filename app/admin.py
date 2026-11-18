import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import (Ad, Announcement, Post, MarketplaceItem, LostFoundItem,
                        AdminSession, Report,
                        Advertiser, AdCampaign, Advertisement, AdPlacement, AdPayment, AdDailyStat)
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin_bp', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_upload(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = uuid.uuid4().hex + '.' + ext
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

def require_admin():
    token = request.headers.get('X-Admin-Token')
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(hours=24)
    session = AdminSession.query.filter(
        AdminSession.token == token,
        AdminSession.created_at >= cutoff
    ).first()
    return session

def ad_to_dict(a):
    return {'id': a.id, 'title': a.title, 'body': a.body, 'image_path': a.image_path,
            'link_url': a.link_url, 'active': a.active, 'click_count': a.click_count,
            'created_at': a.created_at.isoformat()}

@admin_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    d = request.get_json()
    if not d or d.get('username') != 'Adminmungai' or d.get('password') != 'Mungai2300':
        return jsonify({'error': 'Invalid credentials'}), 401
    token = uuid.uuid4().hex
    s = AdminSession(token=token)
    db.session.add(s); db.session.commit()
    return jsonify({'token': token})

@admin_bp.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    token = request.headers.get('X-Admin-Token')
    if token:
        AdminSession.query.filter_by(token=token).delete()
        db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/admin/ads', methods=['GET'])
def list_ads():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify([ad_to_dict(a) for a in Ad.query.order_by(Ad.created_at.desc()).all()])

@admin_bp.route('/api/admin/ads', methods=['POST'])
def create_ad():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    image_path = None
    if 'image' in request.files:
        image_path = save_upload(request.files['image'])
    d = request.form if request.form else request.get_json() or {}
    if not d.get('title') or not d.get('body'):
        return jsonify({'error': 'Missing fields'}), 400
    ad = Ad(title=d['title'], body=d['body'], image_path=image_path,
            link_url=d.get('link_url',''), active=d.get('active', 'true') in [True, 'true', '1'])
    db.session.add(ad); db.session.commit()
    return jsonify(ad_to_dict(ad)), 201

@admin_bp.route('/api/admin/ads/<int:aid>', methods=['PUT'])
def edit_ad(aid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    ad = Ad.query.get_or_404(aid)
    if 'image' in request.files:
        fn = save_upload(request.files['image'])
        if fn: ad.image_path = fn
    d = request.form if request.form else request.get_json() or {}
    if 'title' in d: ad.title = d['title']
    if 'body' in d: ad.body = d['body']
    if 'link_url' in d: ad.link_url = d['link_url']
    if 'active' in d: ad.active = d['active'] in [True, 'true', '1']
    db.session.commit()
    return jsonify(ad_to_dict(ad))

@admin_bp.route('/api/admin/ads/<int:aid>', methods=['DELETE'])
def delete_ad(aid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    ad = Ad.query.get_or_404(aid)
    db.session.delete(ad); db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/admin/announcements', methods=['POST'])
def create_announcement():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json()
    if not d or not d.get('title') or not d.get('body'):
        return jsonify({'error': 'Missing fields'}), 400
    a = Announcement(title=d['title'], body=d['body'], pinned=d.get('pinned', False))
    db.session.add(a); db.session.commit()
    return jsonify({'id': a.id}), 201

@admin_bp.route('/api/admin/announcements/<int:aid>', methods=['DELETE'])
def delete_announcement(aid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    a = Announcement.query.get_or_404(aid)
    db.session.delete(a); db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/admin/posts/<int:pid>', methods=['DELETE'])
def delete_post(pid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    p = Post.query.get_or_404(pid)
    p.deleted = True; db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/admin/marketplace/<int:mid>', methods=['DELETE'])
def delete_marketplace(mid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    m = MarketplaceItem.query.get_or_404(mid)
    m.deleted = True; db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/admin/lostandfound/<int:lid>', methods=['DELETE'])
def delete_lostandfound(lid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    l = LostFoundItem.query.get_or_404(lid)
    l.deleted = True; db.session.commit()
    return jsonify({'ok': True})

@admin_bp.route('/api/admin/reports', methods=['GET'])
def list_reports():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    reports = Report.query.filter_by(resolved=False).order_by(Report.created_at.desc()).all()
    result = []
    for r in reports:
        entry = {
            'id': r.id,
            'content_type': r.content_type,
            'content_id': r.content_id,
            'reason': r.reason,
            'reporter_ip': r.reporter_ip,
            'created_at': r.created_at.isoformat(),
            'content_preview': ''
        }
        if r.content_type == 'post':
            item = Post.query.get(r.content_id)
            if item:
                entry['content_preview'] = item.title
        elif r.content_type == 'marketplace':
            item = MarketplaceItem.query.get(r.content_id)
            if item:
                entry['content_preview'] = item.title
        elif r.content_type == 'lostandfound':
            item = LostFoundItem.query.get(r.content_id)
            if item:
                entry['content_preview'] = item.title
        result.append(entry)
    return jsonify(result)

@admin_bp.route('/api/admin/reports/<int:rid>/resolve', methods=['POST'])
def resolve_report(rid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    report = Report.query.get_or_404(rid)
    report.resolved = True
    db.session.commit()
    return jsonify({'ok': True})


# ---- Advertiser Management ----

@admin_bp.route('/api/admin/advertisers', methods=['GET'])
def admin_list_advertisers():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    advs = Advertiser.query.order_by(Advertiser.created_at.desc()).all()
    return jsonify([a.to_dict() for a in advs])


@admin_bp.route('/api/admin/advertisers/<int:aid>/approve', methods=['PUT'])
def admin_approve_advertiser(aid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    adv = Advertiser.query.get_or_404(aid)
    adv.status = 'approved'
    adv.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/advertisers/<int:aid>/reject', methods=['PUT'])
def admin_reject_advertiser(aid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    adv = Advertiser.query.get_or_404(aid)
    adv.status = 'rejected'
    db.session.commit()
    return jsonify({'ok': True})


# ---- Campaign Management ----

@admin_bp.route('/api/admin/campaigns', methods=['GET'])
def admin_list_campaigns():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    campaigns = AdCampaign.query.order_by(AdCampaign.created_at.desc()).all()
    result = []
    for c in campaigns:
        d = c.to_dict()
        d['advertiser_name'] = c.advertiser.business_name if c.advertiser else ''
        result.append(d)
    return jsonify(result)


def _set_campaign_status(campaign_id, new_status):
    campaign = AdCampaign.query.get_or_404(campaign_id)
    campaign.status = new_status
    Advertisement.query.filter_by(campaign_id=campaign_id).update({'status': new_status})
    db.session.commit()
    return campaign


@admin_bp.route('/api/admin/campaigns/<int:cid>/approve', methods=['PUT'])
def admin_approve_campaign(cid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    _set_campaign_status(cid, 'approved')
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/campaigns/<int:cid>/reject', methods=['PUT'])
def admin_reject_campaign(cid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    _set_campaign_status(cid, 'rejected')
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/campaigns/<int:cid>/pause', methods=['PUT'])
def admin_pause_campaign(cid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    _set_campaign_status(cid, 'paused')
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/campaigns/<int:cid>/activate', methods=['PUT'])
def admin_activate_campaign(cid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    _set_campaign_status(cid, 'active')
    return jsonify({'ok': True})


# ---- Placement Management ----

@admin_bp.route('/api/admin/placements', methods=['GET'])
def admin_list_placements():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    placements = AdPlacement.query.order_by(AdPlacement.name).all()
    return jsonify([p.to_dict() for p in placements])


@admin_bp.route('/api/admin/placements', methods=['POST'])
def admin_create_placement():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json(silent=True) or {}
    name = (d.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    try:
        price = float(d.get('price_per_day', 0))
    except (ValueError, TypeError):
        price = 0.0
    if price < 0:
        return jsonify({'error': 'price_per_day must be non-negative'}), 400
    p = AdPlacement(
        name=name,
        description=(d.get('description') or '').strip() or None,
        price_per_day=price,
        active=bool(d.get('active', True))
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201


@admin_bp.route('/api/admin/placements/<int:pid>', methods=['PUT'])
def admin_update_placement(pid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    p = AdPlacement.query.get_or_404(pid)
    d = request.get_json(silent=True) or {}
    if 'name' in d:
        p.name = (d['name'] or '').strip()
    if 'description' in d:
        p.description = (d['description'] or '').strip() or None
    if 'price_per_day' in d:
        try:
            p.price_per_day = float(d['price_per_day'])
        except (ValueError, TypeError):
            pass
    if 'active' in d:
        p.active = bool(d['active'])
    db.session.commit()
    return jsonify(p.to_dict())


# ---- Revenue & Payments ----

@admin_bp.route('/api/admin/revenue', methods=['GET'])
def admin_revenue():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    confirmed_revenue = db.session.query(
        db.func.sum(AdPayment.amount)
    ).filter_by(status='confirmed').scalar() or 0.0
    return jsonify({
        'total_campaigns': AdCampaign.query.count(),
        'confirmed_revenue': confirmed_revenue,
        'unpaid_campaigns': AdCampaign.query.filter_by(payment_status='unpaid').count(),
        'paid_campaigns': AdCampaign.query.filter_by(payment_status='paid').count(),
    })


@admin_bp.route('/api/admin/payments', methods=['GET'])
def admin_list_payments():
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    payments = AdPayment.query.order_by(AdPayment.created_at.desc()).all()
    result = []
    for pay in payments:
        d = pay.to_dict()
        d['campaign_name'] = pay.campaign.name if pay.campaign else ''
        result.append(d)
    return jsonify(result)


@admin_bp.route('/api/admin/payments/<int:pid>/confirm', methods=['PUT'])
def admin_confirm_payment(pid):
    if not require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    # Fix 5: create or update AdPayment and update campaign payment_status
    payment = AdPayment.query.get_or_404(pid)
    payment.status = 'confirmed'
    payment.confirmed_at = datetime.utcnow()
    campaign = AdCampaign.query.get(payment.campaign_id)
    if campaign:
        campaign.payment_status = 'paid'
    db.session.commit()
    return jsonify({'ok': True})
