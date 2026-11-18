import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from app import db
from app.models import (
    Institution, InstitutionCategory, InstitutionCommunity,
    InstitutionPost, InstitutionPostComment, AdminSession
)

institutions_bp = Blueprint('institutions', __name__, url_prefix='/api/institutions')


def _require_admin():
    token = request.headers.get('X-Admin-Token', '')
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(hours=24)
    session = AdminSession.query.filter_by(token=token).filter(
        AdminSession.created_at >= cutoff
    ).first()
    return session


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@institutions_bp.route('', methods=['GET'])
def list_institutions():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    county = request.args.get('county', '').strip()
    ownership = request.args.get('ownership', '').strip()
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(1, int(request.args.get('per_page', 50))))

    query = Institution.query.filter_by(active=True)

    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Institution.name.ilike(like),
                Institution.abbreviation.ilike(like),
                Institution.county.ilike(like)
            )
        )
    if category:
        query = query.join(InstitutionCategory).filter(InstitutionCategory.name == category)
    if county:
        query = query.filter(Institution.county.ilike(f'%{county}%'))
    if ownership:
        query = query.filter(Institution.ownership.ilike(ownership))

    query = query.order_by(Institution.name)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    result = []
    for inst in items:
        d = inst.to_dict()
        if inst.community:
            d['member_count'] = inst.community.member_count
            d['post_count'] = inst.community.post_count
        else:
            d['member_count'] = 0
            d['post_count'] = 0
        result.append(d)

    return jsonify({'institutions': result, 'total': total, 'page': page, 'pages': pages})


@institutions_bp.route('/categories', methods=['GET'])
def list_categories():
    cats = InstitutionCategory.query.order_by(InstitutionCategory.name).all()
    return jsonify({'categories': [c.to_dict() for c in cats]})


@institutions_bp.route('/counties', methods=['GET'])
def list_counties():
    rows = db.session.query(Institution.county).filter(
        Institution.active == True,
        Institution.county.isnot(None)
    ).distinct().order_by(Institution.county).all()
    counties = [r[0] for r in rows if r[0]]
    return jsonify({'counties': counties})


@institutions_bp.route('/popular', methods=['GET'])
def popular_institutions():
    communities = InstitutionCommunity.query.order_by(
        InstitutionCommunity.member_count.desc()
    ).limit(10).all()
    result = []
    for comm in communities:
        inst = Institution.query.get(comm.institution_id)
        if inst and inst.active:
            d = inst.to_dict()
            d['member_count'] = comm.member_count
            d['post_count'] = comm.post_count
            result.append(d)
    return jsonify({'institutions': result})


@institutions_bp.route('/<int:id>', methods=['GET'])
def get_institution(id):
    inst = Institution.query.get_or_404(id)
    d = inst.to_dict()
    if inst.community:
        d['community'] = inst.community.to_dict()
    else:
        d['community'] = None
    return jsonify(d)


@institutions_bp.route('/<int:id>/posts', methods=['GET'])
def list_inst_posts(id):
    Institution.query.get_or_404(id)
    page = max(1, int(request.args.get('page', 1)))
    per_page = 20
    query = InstitutionPost.query.filter_by(institution_id=id, deleted=False).order_by(
        InstitutionPost.created_at.desc()
    )
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return jsonify({'posts': [p.to_dict() for p in items], 'total': total, 'page': page, 'pages': pages})


@institutions_bp.route('/<int:id>/posts', methods=['POST'])
def create_inst_post(id):
    inst = Institution.query.get_or_404(id)
    data = request.get_json() or {}
    poster_name = (data.get('poster_name') or '').strip()
    title = (data.get('title') or '').strip()
    body = (data.get('body') or '').strip()
    if not poster_name or not title:
        return jsonify({'error': 'poster_name and title are required'}), 400
    if not body:
        return jsonify({'error': 'body is required'}), 400

    comm = inst.community
    if not comm:
        comm = InstitutionCommunity(institution_id=inst.id)
        db.session.add(comm)
        db.session.flush()

    post = InstitutionPost(
        institution_id=inst.id,
        community_id=comm.id,
        poster_name=poster_name,
        poster_contact=(data.get('poster_contact') or '').strip() or None,
        title=title,
        body=body,
        topic=data.get('topic', 'General')
    )
    db.session.add(post)
    comm.post_count = (comm.post_count or 0) + 1
    db.session.commit()
    return jsonify(post.to_dict()), 201


@institutions_bp.route('/<int:id>/join', methods=['POST'])
def join_institution(id):
    inst = Institution.query.get_or_404(id)
    comm = inst.community
    if not comm:
        comm = InstitutionCommunity(institution_id=inst.id)
        db.session.add(comm)
        db.session.flush()
    comm.member_count = (comm.member_count or 0) + 1
    db.session.commit()
    return jsonify({'member_count': comm.member_count})


@institutions_bp.route('/<int:id>/posts/<int:pid>/comments', methods=['GET'])
def list_inst_post_comments(id, pid):
    post = InstitutionPost.query.filter_by(id=pid, institution_id=id).first_or_404()
    comments = InstitutionPostComment.query.filter_by(post_id=post.id).order_by(
        InstitutionPostComment.created_at
    ).all()
    return jsonify({'comments': [c.to_dict() for c in comments]})


@institutions_bp.route('/<int:id>/posts/<int:pid>/comments', methods=['POST'])
def add_inst_post_comment(id, pid):
    post = InstitutionPost.query.filter_by(id=pid, institution_id=id).first_or_404()
    data = request.get_json() or {}
    poster_name = (data.get('poster_name') or '').strip()
    body = (data.get('body') or '').strip()
    if not poster_name or not body:
        return jsonify({'error': 'poster_name and body are required'}), 400
    comment = InstitutionPostComment(post_id=post.id, poster_name=poster_name, body=body)
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


@institutions_bp.route('/<int:id>/posts/<int:pid>', methods=['PUT'])
def edit_inst_post(id, pid):
    post = InstitutionPost.query.filter_by(id=pid, institution_id=id).first_or_404()
    data = request.get_json() or {}
    poster_name = (data.get('poster_name') or '').strip()
    if not poster_name or poster_name.lower() != post.poster_name.lower():
        return jsonify({'error': 'poster_name does not match'}), 403
    if 'title' in data and data['title']:
        post.title = data['title'].strip()
    if 'body' in data and data['body']:
        post.body = data['body'].strip()
    if 'topic' in data and data['topic']:
        post.topic = data['topic']
    db.session.commit()
    return jsonify(post.to_dict())


# ---------------------------------------------------------------------------
# Admin routes — same blueprint, /api/admin/institutions prefix via URL rules
# ---------------------------------------------------------------------------

@institutions_bp.route('/admin-list', methods=['GET'])
def admin_list_institutions():
    if not _require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    insts = Institution.query.order_by(Institution.name).all()
    result = []
    for inst in insts:
        d = inst.to_dict()
        if inst.community:
            d['community'] = inst.community.to_dict()
        result.append(d)
    return jsonify({'institutions': result})


@institutions_bp.route('/admin-create', methods=['POST'])
def admin_create_institution():
    if not _require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    # Check duplicate
    existing = Institution.query.filter(
        db.func.lower(Institution.name) == name.lower()
    ).first()
    if existing:
        return jsonify({'error': 'Institution already exists'}), 409

    cat = None
    if data.get('category'):
        cat = InstitutionCategory.query.filter_by(name=data['category']).first()

    inst = Institution(
        name=name,
        abbreviation=data.get('abbreviation') or None,
        category_id=cat.id if cat else None,
        ownership=data.get('ownership', 'Public'),
        county=data.get('county') or None,
        town=data.get('town') or None,
        website=data.get('website') or None,
        source=data.get('source') or None,
        active=True
    )
    db.session.add(inst)
    db.session.flush()
    comm = InstitutionCommunity(institution_id=inst.id)
    db.session.add(comm)
    db.session.commit()
    d = inst.to_dict()
    d['community'] = comm.to_dict()
    return jsonify(d), 201


@institutions_bp.route('/admin-update/<int:id>', methods=['PUT'])
def admin_update_institution(id):
    if not _require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    inst = Institution.query.get_or_404(id)
    data = request.get_json() or {}
    if 'name' in data and data['name']:
        inst.name = data['name'].strip()
    if 'abbreviation' in data:
        inst.abbreviation = data['abbreviation'] or None
    if 'category' in data and data['category']:
        cat = InstitutionCategory.query.filter_by(name=data['category']).first()
        if cat:
            inst.category_id = cat.id
    if 'ownership' in data and data['ownership']:
        inst.ownership = data['ownership']
    if 'county' in data:
        inst.county = data['county'] or None
    if 'town' in data:
        inst.town = data['town'] or None
    if 'website' in data:
        inst.website = data['website'] or None
    if 'source' in data:
        inst.source = data['source'] or None
    if 'active' in data:
        inst.active = bool(data['active'])
    db.session.commit()
    return jsonify(inst.to_dict())


@institutions_bp.route('/admin-deactivate/<int:id>', methods=['DELETE'])
def admin_deactivate_institution(id):
    if not _require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    inst = Institution.query.get_or_404(id)
    inst.active = False
    db.session.commit()
    return jsonify({'message': 'deactivated'})


@institutions_bp.route('/admin-import-csv', methods=['POST'])
def admin_import_csv():
    if not _require_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    content = f.read().decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(content))
    added = 0
    skipped = 0
    for row in reader:
        name = (row.get('name') or '').strip()
        if not name:
            skipped += 1
            continue
        existing = Institution.query.filter(
            db.func.lower(Institution.name) == name.lower()
        ).first()
        if existing:
            skipped += 1
            continue
        cat_name = (row.get('category') or '').strip()
        cat = InstitutionCategory.query.filter_by(name=cat_name).first() if cat_name else None
        inst = Institution(
            name=name,
            abbreviation=(row.get('abbreviation') or '').strip() or None,
            category_id=cat.id if cat else None,
            ownership=(row.get('ownership') or 'Public').strip(),
            county=(row.get('county') or '').strip() or None,
            town=(row.get('town') or '').strip() or None,
            website=(row.get('website') or '').strip() or None,
            source=(row.get('source') or '').strip() or None,
            active=True
        )
        db.session.add(inst)
        db.session.flush()
        comm = InstitutionCommunity(institution_id=inst.id)
        db.session.add(comm)
        added += 1
    db.session.commit()
    return jsonify({'added': added, 'skipped': skipped})


# ---------------------------------------------------------------------------
# /api/admin/institutions — separate URL prefix via app-level registration
# These duplicate-route aliases let the admin JS call /api/admin/institutions
# ---------------------------------------------------------------------------

admin_inst_bp = Blueprint('admin_institutions', __name__, url_prefix='/api/admin/institutions')


def _require_admin_admin():
    token = request.headers.get('X-Admin-Token', '')
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return AdminSession.query.filter_by(token=token).filter(
        AdminSession.created_at >= cutoff
    ).first()


@admin_inst_bp.route('', methods=['GET'])
def admin_list():
    if not _require_admin_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    insts = Institution.query.order_by(Institution.name).all()
    result = []
    for inst in insts:
        d = inst.to_dict()
        if inst.community:
            d['community'] = inst.community.to_dict()
        result.append(d)
    return jsonify({'institutions': result})


@admin_inst_bp.route('', methods=['POST'])
def admin_create():
    if not _require_admin_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    existing = Institution.query.filter(
        db.func.lower(Institution.name) == name.lower()
    ).first()
    if existing:
        return jsonify({'error': 'Institution already exists'}), 409
    cat = None
    if data.get('category'):
        cat = InstitutionCategory.query.filter_by(name=data['category']).first()
    inst = Institution(
        name=name,
        abbreviation=data.get('abbreviation') or None,
        category_id=cat.id if cat else None,
        ownership=data.get('ownership', 'Public'),
        county=data.get('county') or None,
        town=data.get('town') or None,
        website=data.get('website') or None,
        source=data.get('source') or None,
        active=True
    )
    db.session.add(inst)
    db.session.flush()
    comm = InstitutionCommunity(institution_id=inst.id)
    db.session.add(comm)
    db.session.commit()
    d = inst.to_dict()
    d['community'] = comm.to_dict()
    return jsonify(d), 201


@admin_inst_bp.route('/<int:id>', methods=['PUT'])
def admin_update(id):
    if not _require_admin_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    inst = Institution.query.get_or_404(id)
    data = request.get_json() or {}
    if 'name' in data and data['name']:
        inst.name = data['name'].strip()
    if 'abbreviation' in data:
        inst.abbreviation = data['abbreviation'] or None
    if 'category' in data and data['category']:
        cat = InstitutionCategory.query.filter_by(name=data['category']).first()
        if cat:
            inst.category_id = cat.id
    if 'ownership' in data and data['ownership']:
        inst.ownership = data['ownership']
    if 'county' in data:
        inst.county = data['county'] or None
    if 'town' in data:
        inst.town = data['town'] or None
    if 'website' in data:
        inst.website = data['website'] or None
    if 'source' in data:
        inst.source = data['source'] or None
    if 'active' in data:
        inst.active = bool(data['active'])
    db.session.commit()
    return jsonify(inst.to_dict())


@admin_inst_bp.route('/<int:id>', methods=['DELETE'])
def admin_deactivate(id):
    if not _require_admin_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    inst = Institution.query.get_or_404(id)
    inst.active = False
    db.session.commit()
    return jsonify({'message': 'deactivated'})


@admin_inst_bp.route('/import-csv', methods=['POST'])
def admin_import(  ):
    if not _require_admin_admin():
        return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    f = request.files['file']
    content = f.read().decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(content))
    added = 0
    skipped = 0
    for row in reader:
        name = (row.get('name') or '').strip()
        if not name:
            skipped += 1
            continue
        existing = Institution.query.filter(
            db.func.lower(Institution.name) == name.lower()
        ).first()
        if existing:
            skipped += 1
            continue
        cat_name = (row.get('category') or '').strip()
        cat = InstitutionCategory.query.filter_by(name=cat_name).first() if cat_name else None
        inst = Institution(
            name=name,
            abbreviation=(row.get('abbreviation') or '').strip() or None,
            category_id=cat.id if cat else None,
            ownership=(row.get('ownership') or 'Public').strip(),
            county=(row.get('county') or '').strip() or None,
            town=(row.get('town') or '').strip() or None,
            website=(row.get('website') or '').strip() or None,
            source=(row.get('source') or '').strip() or None,
            active=True
        )
        db.session.add(inst)
        db.session.flush()
        comm = InstitutionCommunity(institution_id=inst.id)
        db.session.add(comm)
        added += 1
    db.session.commit()
    return jsonify({'added': added, 'skipped': skipped})
