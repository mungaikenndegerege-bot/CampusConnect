import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Ad, Announcement, Post, MarketplaceItem, LostFoundItem, AdminSession
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
    if not d or d.get('username') != 'Adminmungai' or d.get('password') != 'Mbatia2000':
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
