import hashlib
import hmac
import secrets

from flask import current_app


def issue_owner_token(resource_type=None, idempotency_key=None):
    if resource_type and idempotency_key:
        token = hmac.new(
            current_app.config['SECRET_KEY'].encode('utf-8'),
            f'{resource_type}:{idempotency_key}'.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
    else:
        token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    return token, token_hash


def idempotency_key_hash(resource_type, raw_key):
    if raw_key is None:
        return None
    if len(raw_key) < 16 or len(raw_key) > 200:
        raise ValueError('Idempotency-Key must be between 16 and 200 characters.')
    return hashlib.sha256(f'{resource_type}:{raw_key}'.encode('utf-8')).hexdigest()


def find_idempotent_record(resource_type, key_hash, model):
    if not key_hash:
        return None
    from app import db
    from app.models import IdempotencyRecord
    record = IdempotencyRecord.query.filter_by(
        resource_type=resource_type, key_hash=key_hash
    ).first()
    return db.session.get(model, record.resource_id) if record else None


def remember_idempotent_record(resource_type, key_hash, record):
    if not key_hash:
        return
    from app import db
    from app.models import IdempotencyRecord
    db.session.flush()
    db.session.add(IdempotencyRecord(
        resource_type=resource_type,
        key_hash=key_hash,
        resource_id=record.id,
    ))


def verify_owner_token(record, token):
    if not token or not record.owner_token_hash:
        return False
    candidate_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    return hmac.compare_digest(record.owner_token_hash, candidate_hash)


def required_text(data, key, maximum, minimum=1):
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f'{key} must be text.')
    value = value.strip()
    if len(value) < minimum or len(value) > maximum:
        raise ValueError(f'{key} must be between {minimum} and {maximum} characters.')
    return value


def optional_text(data, key, maximum):
    value = data.get(key, '')
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError(f'{key} must be text.')
    value = value.strip()
    if len(value) > maximum:
        raise ValueError(f'{key} must not exceed {maximum} characters.')
    return value
