import uuid
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import Account, AccountSession
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
            'bio': a.bio, 'created_at': a.created_at.isoformat()}

@accounts_bp.route('/api/accounts/register', methods=['POST'])
@check_rate_limit(3, 3600)
def register():
    d = request.get_json()
    if not d:
        return jsonify({'error': 'Missing body'}), 400
    name = (d.get('name') or '').strip()
    email = (d.get('email') or '').strip().lower()
    password = d.get('password') or ''
    if len(name) < 2 or len(name) > 100:
        return jsonify({'error': 'Name must be 2-100 characters'}), 400
    if not EMAIL_RE.match(email):
        return jsonify({'error': 'Invalid email address'}), 400
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    if Account.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409
    account = Account(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(account)
    db.session.flush()
    token = uuid.uuid4().hex
    session = AccountSession(account_id=account.id, token=token)
    db.session.add(session)
    db.session.commit()
    return jsonify({'token': token, 'account': account_to_dict(account)}), 201

@accounts_bp.route('/api/accounts/login', methods=['POST'])
def login():
    d = request.get_json()
    if not d:
        return jsonify({'error': 'Missing body'}), 400
    email = (d.get('email') or '').strip().lower()
    password = d.get('password') or ''
    account = Account.query.filter_by(email=email, active=True).first()
    if not account or not check_password_hash(account.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401
    token = uuid.uuid4().hex
    session = AccountSession(account_id=account.id, token=token)
    db.session.add(session)
    db.session.commit()
    return jsonify({'token': token, 'account': account_to_dict(account)})

@accounts_bp.route('/api/accounts/me', methods=['GET'])
def get_me():
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(account_to_dict(account))

@accounts_bp.route('/api/accounts/me', methods=['PUT'])
def update_me():
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json() or {}
    if 'name' in d:
        name = d['name'].strip()
        if len(name) < 2 or len(name) > 100:
            return jsonify({'error': 'Name must be 2-100 characters'}), 400
        account.name = name
    if 'bio' in d:
        account.bio = d['bio']
    db.session.commit()
    return jsonify(account_to_dict(account))

@accounts_bp.route('/api/accounts/logout', methods=['POST'])
def logout():
    token = request.headers.get('X-Account-Token')
    if token:
        AccountSession.query.filter_by(token=token).delete()
        db.session.commit()
    return jsonify({'ok': True})
