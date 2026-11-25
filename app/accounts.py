import secrets
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import Account, AccountSession, Institution
from app.ratelimit import check_rate_limit

accounts_bp = Blueprint('accounts_bp', __name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
SESSION_DAYS = 30

def _get_account(token):
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(days=SESSION_DAYS)
    s = AccountSession.query.filter(
        AccountSession.token == token,
        AccountSession.created_at >= cutoff
    ).first()
    return s.account if s else None

def account_to_dict(a):
    return {'id': a.id, 'name': a.name, 'email': a.email,
            'bio': a.bio, 'institution_id': a.institution_id,
            'institution_name': a.institution.name if a.institution else None,
            'created_at': a.created_at.isoformat()}

@accounts_bp.route('/api/accounts/register', methods=['POST'])
@check_rate_limit(3, 3600)
def register():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    name = d.get('name')
    email = d.get('email')
    password = d.get('password')
    if not isinstance(name, str) or not isinstance(email, str) or not isinstance(password, str):
        return jsonify({'error': 'Name, email, and password must be text.'}), 400
    name = name.strip()
    email = email.strip().lower()
    if len(name) < 2 or len(name) > 100:
        return jsonify({'error': 'Name must be 2-100 characters'}), 400
    if len(email) > 200 or not EMAIL_RE.match(email):
        return jsonify({'error': 'Invalid email address'}), 400
    if len(password) < 8 or len(password) > 128:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if Account.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    account = Account(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )
    token = secrets.token_urlsafe(32)
    db.session.add(account)
    try:
        db.session.flush()
        db.session.add(AccountSession(account_id=account.id, token=token))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Email already registered'}), 409
    return jsonify({'token': token, 'account': account_to_dict(account)}), 201

@accounts_bp.route('/api/accounts/login', methods=['POST'])
@check_rate_limit(10, 900)
def login():
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    email = d.get('email')
    password = d.get('password')
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({'error': 'Email and password must be text.'}), 400
    email = email.strip().lower()
    account = Account.query.filter_by(email=email, active=True).first()
    if not account or not check_password_hash(account.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = secrets.token_urlsafe(32)
    session = AccountSession(account_id=account.id, token=token)
    db.session.add(session)
    db.session.commit()
    return jsonify({'token': token, 'account': account_to_dict(account)})

@accounts_bp.route('/api/accounts/me', methods=['GET'])
def get_me():
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account or not account.active:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(account_to_dict(account))

@accounts_bp.route('/api/accounts/me', methods=['PUT'])
def update_me():
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account or not account.active:
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    if 'name' in d:
        name = d['name'].strip() if isinstance(d['name'], str) else ''
        if len(name) < 2 or len(name) > 100:
            return jsonify({'error': 'Name must be 2-100 characters'}), 400
        account.name = name
    if 'bio' in d:
        if not isinstance(d['bio'], str) or len(d['bio']) > 2000:
            return jsonify({'error': 'Bio must be text of at most 2000 characters'}), 400
        account.bio = d['bio']
    if 'institution_id' in d:
        try:
            institution_id = int(d['institution_id']) if d['institution_id'] is not None else None
        except (TypeError, ValueError):
            return jsonify({'error': 'institution_id must be an integer or null'}), 400
        if institution_id is not None and not Institution.query.filter_by(
                id=institution_id, active=True).first():
            return jsonify({'error': 'Institution not found'}), 404
        account.institution_id = institution_id
    db.session.commit()
    return jsonify(account_to_dict(account))

@accounts_bp.route('/api/accounts/logout', methods=['POST'])
def logout():
    token = request.headers.get('X-Account-Token')
    if token:
        AccountSession.query.filter_by(token=token).delete()
        db.session.commit()
    return jsonify({'ok': True})
