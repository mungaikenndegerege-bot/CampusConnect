import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db
from app.models import (
    Post, Comment, MarketplaceItem, LostFoundItem, Announcement, Ad, Report,
    AdminSession, Institution, InstitutionCategory, InstitutionPost, FeaturePost
)
from app.ratelimit import check_rate_limit

public_bp = Blueprint('public_bp', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_upload(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        import uuid
        ext = filename.rsplit('.', 1)[1].lower()
        filename = uuid.uuid4().hex + '.' + ext
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

def post_to_dict(p):
    return {'id': p.id, 'poster_name': p.poster_name, 'poster_contact': p.poster_contact,
            'title': p.title, 'body': p.body, 'topic': p.topic,
            'created_at': p.created_at.isoformat(), 'section': 'community',
            'comment_count': len(p.comments) if p.comments else 0,
            'file_url': f'/api/uploads/{p.file_path}' if p.file_path else None,
            'file_type': p.file_type}

def market_to_dict(m):
    return {'id': m.id, 'poster_name': m.poster_name, 'poster_contact': m.poster_contact,
            'title': m.title, 'description': m.description, 'price': m.price,
            'category': m.category, 'image_path': m.image_path,
            'created_at': m.created_at.isoformat(), 'sold': m.sold, 'section': 'marketplace'}

def lf_to_dict(l):
    return {'id': l.id, 'poster_name': l.poster_name, 'poster_contact': l.poster_contact,
            'item_type': l.item_type, 'title': l.title, 'description': l.description,
            'location': l.location, 'created_at': l.created_at.isoformat(),
            'resolved': l.resolved, 'section': 'lostandfound'}

def ann_to_dict(a):
    return {'id': a.id, 'title': a.title, 'body': a.body,
            'created_at': a.created_at.isoformat(), 'pinned': a.pinned, 'section': 'announcement'}

def ad_to_dict(a):
    return {'id': a.id, 'title': a.title, 'body': a.body, 'image_path': a.image_path,
            'link_url': a.link_url, 'active': a.active, 'click_count': a.click_count,
            'created_at': a.created_at.isoformat(), 'type': 'ad'}

@public_bp.route('/api/feed')
def get_feed():
    posts = [post_to_dict(p) for p in Post.query.filter_by(deleted=False).order_by(Post.created_at.desc()).limit(20).all()]
    market = [market_to_dict(m) for m in MarketplaceItem.query.filter_by(deleted=False).order_by(MarketplaceItem.created_at.desc()).limit(20).all()]
    lf = [lf_to_dict(l) for l in LostFoundItem.query.filter_by(deleted=False).order_by(LostFoundItem.created_at.desc()).limit(20).all()]
    anns = [ann_to_dict(a) for a in Announcement.query.order_by(Announcement.created_at.desc()).limit(10).all()]
    combined = sorted(posts + market + lf + anns, key=lambda x: x['created_at'], reverse=True)[:50]
    return jsonify(combined)


@public_bp.route('/api/search')
def search():
    term = request.args.get('q', '').strip()
    if not term or len(term) > 100:
        return jsonify({'error': 'Enter a search term of 1-100 characters.'}), 400

    escaped_term = term.replace('%', '\\%').replace('_', '\\_')
    pattern = f'%{escaped_term}%'
    results = []

    def add_results(query, section, title_getter, body_getter, meta_getter=lambda item: ''):
        for item in query.limit(8).all():
            result = {
                'id': item.id,
                'section': section,
                'title': title_getter(item),
                'body': body_getter(item)[:220],
                'meta': meta_getter(item)
            }
            if section == 'features':
                result['kind'] = item.kind
            results.append(result)

    add_results(
        Post.query.filter(
            Post.deleted.is_(False),
            db.or_(Post.title.ilike(pattern, escape='\\'),
                   Post.body.ilike(pattern, escape='\\'),
                   Post.topic.ilike(pattern, escape='\\'))
        ).order_by(Post.created_at.desc()),
        'community', lambda item: item.title, lambda item: item.body,
        lambda item: f'Community · {item.topic or "General"}'
    )
    add_results(
        MarketplaceItem.query.filter(
            MarketplaceItem.deleted.is_(False),
            MarketplaceItem.sold.is_(False),
            db.or_(MarketplaceItem.title.ilike(pattern, escape='\\'),
                   MarketplaceItem.description.ilike(pattern, escape='\\'),
                   MarketplaceItem.category.ilike(pattern, escape='\\'))
        ).order_by(MarketplaceItem.created_at.desc()),
        'marketplace', lambda item: item.title, lambda item: item.description,
        lambda item: f'Marketplace · {item.category or "Other"}'
    )
    add_results(
        LostFoundItem.query.filter(
            LostFoundItem.deleted.is_(False),
            LostFoundItem.resolved.is_(False),
            db.or_(LostFoundItem.title.ilike(pattern, escape='\\'),
                   LostFoundItem.description.ilike(pattern, escape='\\'),
                   LostFoundItem.location.ilike(pattern, escape='\\'))
        ).order_by(LostFoundItem.created_at.desc()),
        'lostandfound', lambda item: item.title, lambda item: item.description,
        lambda item: f'{item.item_type.title()} · {item.location}'
    )
    add_results(
        Announcement.query.filter(
            db.or_(Announcement.title.ilike(pattern, escape='\\'),
                   Announcement.body.ilike(pattern, escape='\\'))
        ).order_by(Announcement.pinned.desc(), Announcement.created_at.desc()),
        'announcement', lambda item: item.title, lambda item: item.body,
        lambda item: 'Campus news'
    )
    add_results(
        Institution.query.join(
            InstitutionCategory, isouter=True
        ).filter(
            Institution.active.is_(True),
            db.or_(Institution.name.ilike(pattern, escape='\\'),
                   Institution.abbreviation.ilike(pattern, escape='\\'),
                   Institution.county.ilike(pattern, escape='\\'),
                   Institution.town.ilike(pattern, escape='\\'),
                   InstitutionCategory.name.ilike(pattern, escape='\\'))
        ).order_by(Institution.name),
        'institution', lambda item: item.name,
        lambda item: ' · '.join(value for value in (item.abbreviation, item.town, item.county) if value),
        lambda item: item.category.name if item.category else 'Institution'
    )

    institution_posts = InstitutionPost.query.join(
        Institution, InstitutionPost.institution_id == Institution.id
    ).filter(
        InstitutionPost.deleted.is_(False),
        Institution.active.is_(True),
        db.or_(InstitutionPost.title.ilike(pattern, escape='\\'),
               InstitutionPost.body.ilike(pattern, escape='\\'))
    ).order_by(InstitutionPost.created_at.desc()).limit(8).all()
    for post in institution_posts:
        results.append({
            'id': post.institution_id,
            'section': 'institution',
            'title': post.title,
            'body': post.body[:220],
            'meta': f'{post.institution.name} · Community discussion'
        })

    add_results(
        FeaturePost.query.filter(
            FeaturePost.active.is_(True),
            FeaturePost.kind != 'confessions',
            db.or_(FeaturePost.title.ilike(pattern, escape='\\'),
                   FeaturePost.body.ilike(pattern, escape='\\'),
                   FeaturePost.location.ilike(pattern, escape='\\'),
                   FeaturePost.category.ilike(pattern, escape='\\'))
        ).order_by(FeaturePost.created_at.desc()),
        'features', lambda item: item.title,
        lambda item: item.body,
        lambda item: item.kind.replace('_', ' ').title()
    )

    return jsonify({'results': results[:48], 'query': term})


@public_bp.route('/api/posts', methods=['GET'])
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    q = Post.query.filter_by(deleted=False).order_by(Post.created_at.desc())
    total = q.count()
    items = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({'items': [post_to_dict(p) for p in items], 'total': total, 'page': page, 'pages': (total+per_page-1)//per_page})

@public_bp.route('/api/posts', methods=['POST'])
@check_rate_limit(5, 3600)
def create_post():
    import uuid as _uuid
    file_path = None
    file_type = None
    if request.files and 'attachment' in request.files:
        f = request.files['attachment']
        if f and f.filename:
            ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
            image_exts = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
            file_exts = {'pdf', 'doc', 'docx'}
            f.seek(0, 2)
            size = f.tell()
            f.seek(0)
            if ext in image_exts and size <= 5 * 1024 * 1024:
                filename = _uuid.uuid4().hex + '.' + ext
                f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                file_path = filename
                file_type = 'image'
            elif ext in file_exts and size <= 10 * 1024 * 1024:
                filename = _uuid.uuid4().hex + '.' + ext
                f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                file_path = filename
                file_type = 'file'
        d = request.form
    else:
        d = request.get_json() or {}
    if not d.get('poster_name') or not d.get('title') or not d.get('body'):
        return jsonify({'error': 'Missing required fields'}), 400
    p = Post(poster_name=d['poster_name'], poster_contact=d.get('poster_contact', ''),
             title=d['title'], body=d['body'], topic=d.get('topic', 'General'),
             file_path=file_path, file_type=file_type)
    db.session.add(p)
    db.session.commit()
    return jsonify(post_to_dict(p)), 201

@public_bp.route('/api/posts/<int:pid>/comments', methods=['GET'])
def get_comments(pid):
    post = Post.query.get_or_404(pid)
    return jsonify([{'id': c.id, 'poster_name': c.poster_name, 'body': c.body, 'created_at': c.created_at.isoformat()} for c in post.comments])

@public_bp.route('/api/posts/<int:pid>/comments', methods=['POST'])
def add_comment(pid):
    Post.query.get_or_404(pid)
    d = request.get_json()
    if not d or not d.get('poster_name') or not d.get('body'):
        return jsonify({'error': 'Missing fields'}), 400
    c = Comment(post_id=pid, poster_name=d['poster_name'], body=d['body'])
    db.session.add(c); db.session.commit()
    return jsonify({'id': c.id}), 201

@public_bp.route('/api/marketplace', methods=['GET'])
def get_marketplace():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    q = MarketplaceItem.query.filter_by(deleted=False, sold=False).order_by(MarketplaceItem.created_at.desc())
    total = q.count()
    items = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({'items': [market_to_dict(m) for m in items], 'total': total, 'page': page, 'pages': (total+per_page-1)//per_page})

@public_bp.route('/api/marketplace', methods=['POST'])
@check_rate_limit(3, 3600)
def create_marketplace():
    image_path = None
    if 'image' in request.files:
        image_path = save_upload(request.files['image'])
    d = request.form if request.form else request.get_json() or {}
    if not d.get('poster_name') or not d.get('title') or not d.get('description') or not d.get('poster_contact'):
        return jsonify({'error': 'Missing required fields'}), 400
    m = MarketplaceItem(poster_name=d['poster_name'], poster_contact=d['poster_contact'],
                        title=d['title'], description=d['description'],
                        price=d.get('price',''), category=d.get('category','Other'),
                        image_path=image_path)
    db.session.add(m); db.session.commit()
    return jsonify(market_to_dict(m)), 201

@public_bp.route('/api/lostandfound', methods=['GET'])
def get_lostandfound():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    q = LostFoundItem.query.filter_by(deleted=False, resolved=False).order_by(LostFoundItem.created_at.desc())
    total = q.count()
    items = q.offset((page-1)*per_page).limit(per_page).all()
    return jsonify({'items': [lf_to_dict(l) for l in items], 'total': total, 'page': page, 'pages': (total+per_page-1)//per_page})

@public_bp.route('/api/lostandfound', methods=['POST'])
@check_rate_limit(5, 3600)
def create_lostandfound():
    d = request.get_json()
    if not d or not d.get('poster_name') or not d.get('title') or not d.get('description') or not d.get('location') or not d.get('poster_contact') or not d.get('item_type'):
        return jsonify({'error': 'Missing required fields'}), 400
    l = LostFoundItem(poster_name=d['poster_name'], poster_contact=d['poster_contact'],
                      item_type=d['item_type'], title=d['title'], description=d['description'],
                      location=d['location'])
    db.session.add(l); db.session.commit()
    return jsonify(lf_to_dict(l)), 201

@public_bp.route('/api/posts/<int:pid>', methods=['PUT'])
def update_post(pid):
    post = Post.query.get_or_404(pid)
    d = request.get_json()
    if not d or not d.get('poster_name'):
        return jsonify({'error': 'Missing poster_name'}), 400
    if post.poster_name.strip().lower() != d['poster_name'].strip().lower():
        return jsonify({'error': 'Name does not match the original poster'}), 403
    post.title = d.get('title', post.title)
    post.body = d.get('body', post.body)
    post.topic = d.get('topic', post.topic)
    db.session.commit()
    return jsonify(post_to_dict(post))

@public_bp.route('/api/marketplace/<int:mid>', methods=['PUT'])
def update_marketplace(mid):
    item = MarketplaceItem.query.get_or_404(mid)
    d = request.get_json()
    if not d or not d.get('poster_name'):
        return jsonify({'error': 'Missing poster_name'}), 400
    if item.poster_name.strip().lower() != d['poster_name'].strip().lower():
        return jsonify({'error': 'Name does not match the original poster'}), 403
    item.title = d.get('title', item.title)
    item.description = d.get('description', item.description)
    item.price = d.get('price', item.price)
    item.category = d.get('category', item.category)
    db.session.commit()
    return jsonify(market_to_dict(item))

@public_bp.route('/api/lostandfound/<int:lid>', methods=['PUT'])
def update_lostandfound(lid):
    item = LostFoundItem.query.get_or_404(lid)
    d = request.get_json()
    if not d or not d.get('poster_name'):
        return jsonify({'error': 'Missing poster_name'}), 400
    if item.poster_name.strip().lower() != d['poster_name'].strip().lower():
        return jsonify({'error': 'Name does not match the original poster'}), 403
    item.title = d.get('title', item.title)
    item.description = d.get('description', item.description)
    item.location = d.get('location', item.location)
    item.item_type = d.get('item_type', item.item_type)
    db.session.commit()
    return jsonify(lf_to_dict(item))

@public_bp.route('/api/announcements', methods=['POST'])
def create_announcement():
    from datetime import timedelta
    token = request.headers.get('X-Admin-Token', '')
    if not token or not token.startswith('v2_'):
        return jsonify({'error': 'Only admins can post announcements.'}), 403
    cutoff = datetime.utcnow() - timedelta(hours=24)
    session = AdminSession.query.filter_by(token=token).filter(
        AdminSession.created_at >= cutoff
    ).first()
    if not session:
        return jsonify({'error': 'Only admins can post announcements.'}), 403
    d = request.get_json() or {}
    if not d.get('title') or not d.get('body'):
        return jsonify({'error': 'title and body are required'}), 400
    a = Announcement(title=d['title'], body=d['body'], pinned=bool(d.get('pinned', False)))
    db.session.add(a)
    db.session.commit()
    return jsonify(ann_to_dict(a)), 201

@public_bp.route('/api/announcements')
def get_announcements():
    items = Announcement.query.order_by(Announcement.pinned.desc(), Announcement.created_at.desc()).all()
    return jsonify([ann_to_dict(a) for a in items])

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

@public_bp.route('/api/ads/<int:aid>/click', methods=['POST'])
def click_ad(aid):
    ad = Ad.query.get_or_404(aid)
    ad.click_count += 1
    db.session.commit()
    return jsonify({'ok': True})

@public_bp.route('/api/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@public_bp.route('/api/report', methods=['POST'])
@check_rate_limit(10, 3600)
def create_report():
    d = request.get_json()
    if not d or not d.get('content_type') or not d.get('content_id') or not d.get('reason'):
        return jsonify({'error': 'Missing fields'}), 400
    if d['content_type'] not in ('post', 'marketplace', 'lostandfound'):
        return jsonify({'error': 'Invalid content_type'}), 400
    report = Report(
        content_type=d['content_type'],
        content_id=int(d['content_id']),
        reason=d['reason'],
        reporter_ip=request.remote_addr
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({'ok': True}), 201
