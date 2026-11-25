from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.accounts import _get_account
from app.content_security import (
    find_idempotent_record, idempotency_key_hash, issue_owner_token,
    optional_text, remember_idempotent_record, required_text, verify_owner_token,
)
from app.models import Event, Institution, Notification, Opportunity, Post, Reaction, InstitutionPost
from app.ratelimit import check_rate_limit
from app.storage import StorageError, asset_url, delete_asset, upload_asset

campus_bp = Blueprint('campus_bp', __name__)


def _cleanup_upload(reference):
    try:
        delete_asset(reference)
    except StorageError as exception:
        current_app.logger.error('Could not clean up an unused upload: %s', exception)


def _parse_datetime(value, field, required=False):
    if not value:
        if required:
            raise ValueError(f'{field} is required.')
        return None
    if not isinstance(value, str):
        raise ValueError(f'{field} must be an ISO-8601 date and time.')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exception:
        raise ValueError(f'{field} must be an ISO-8601 date and time.') from exception
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _institution_id(data):
    value = data.get('institution_id')
    if value in (None, ''):
        return None
    try:
        institution_id = int(value)
    except (TypeError, ValueError) as exception:
        raise ValueError('institution_id must be an integer.') from exception
    if not Institution.query.filter_by(id=institution_id, active=True).first():
        raise ValueError('The selected institution is not active.')
    return institution_id


def _event_dict(event):
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'institution_id': event.institution_id,
        'venue': event.venue,
        'starts_at': event.starts_at.isoformat() + 'Z',
        'ends_at': event.ends_at.isoformat() + 'Z' if event.ends_at else None,
        'poster_name': event.poster_name,
        'contact': event.contact,
        'poster_url': asset_url(event.poster_path),
        'created_at': event.created_at.isoformat(),
    }


def _opportunity_dict(item):
    return {
        'id': item.id,
        'opportunity_type': item.opportunity_type,
        'title': item.title,
        'organization': item.organization,
        'description': item.description,
        'location': item.location,
        'application_url': item.application_url,
        'institution_id': item.institution_id,
        'closes_at': item.closes_at.isoformat() + 'Z' if item.closes_at else None,
        'poster_name': item.poster_name,
        'created_at': item.created_at.isoformat(),
    }


@campus_bp.route('/api/events', methods=['GET'])
def list_events():
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(50, max(1, request.args.get('per_page', 20, type=int)))
    query = Event.query.filter_by(active=True)
    institution_id = request.args.get('institution_id', type=int)
    if institution_id:
        query = query.filter_by(institution_id=institution_id)
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(db.or_(
            Event.title.ilike(f'%{search}%'),
            Event.description.ilike(f'%{search}%'),
            Event.venue.ilike(f'%{search}%'),
        ))
    query = query.order_by(Event.starts_at.asc(), Event.id.asc())
    total = query.count()
    events = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'items': [_event_dict(event) for event in events],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page,
    })


@campus_bp.route('/api/events', methods=['POST'])
@check_rate_limit(5, 3600)
def create_event():
    data = request.form if request.form else request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'A JSON object is required.'}), 400
    try:
        title = required_text(data, 'title', 200, 3)
        description = required_text(data, 'description', 5000, 5)
        venue = required_text(data, 'venue', 200, 2)
        poster_name = required_text(data, 'poster_name', 100, 2)
        contact = optional_text(data, 'contact', 100)
        starts_at = _parse_datetime(data.get('starts_at'), 'starts_at', required=True)
        ends_at = _parse_datetime(data.get('ends_at'), 'ends_at')
        institution_id = _institution_id(data)
        if ends_at and ends_at < starts_at:
            raise ValueError('ends_at must be on or after starts_at.')
    except ValueError as exception:
        return jsonify({'error': str(exception)}), 400

    raw_idempotency_key = request.headers.get('Idempotency-Key')
    try:
        key_hash = idempotency_key_hash('event', raw_idempotency_key)
    except ValueError as exception:
        return jsonify({'error': str(exception)}), 400
    existing = find_idempotent_record('event', key_hash, Event)
    if existing:
        response = _event_dict(existing)
        response['owner_token'] = issue_owner_token('event', raw_idempotency_key)[0]
        return jsonify(response), 200

    poster_path = None
    poster = request.files.get('poster')
    if poster and poster.filename:
        poster_path = upload_asset(poster, 'event_poster', 5 * 1024 * 1024,
                                   {'jpg', 'jpeg', 'png', 'webp'})
    owner_token, owner_hash = issue_owner_token('event', raw_idempotency_key)
    event = Event(
        title=title, description=description, venue=venue, poster_name=poster_name,
        contact=contact, starts_at=starts_at, ends_at=ends_at,
        institution_id=institution_id, poster_path=poster_path,
        owner_token_hash=owner_hash,
    )
    db.session.add(event)
    try:
        remember_idempotent_record('event', key_hash, event)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = find_idempotent_record('event', key_hash, Event)
        if not existing:
            if poster_path:
                _cleanup_upload(poster_path)
            raise
        if poster_path:
            _cleanup_upload(poster_path)
        response = _event_dict(existing)
        response['owner_token'] = issue_owner_token('event', raw_idempotency_key)[0]
        return jsonify(response), 200
    response = _event_dict(event)
    response['owner_token'] = owner_token
    return jsonify(response), 201


@campus_bp.route('/api/events/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    event = Event.query.filter_by(id=event_id, active=True).first_or_404()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    if not verify_owner_token(event, data.get('owner_token')):
        return jsonify({'error': 'Valid owner token required.'}), 403
    try:
        event.title = required_text(data, 'title', 200, 3)
        event.description = required_text(data, 'description', 5000, 5)
        event.venue = required_text(data, 'venue', 200, 2)
        event.starts_at = _parse_datetime(data.get('starts_at'), 'starts_at', required=True)
        event.ends_at = _parse_datetime(data.get('ends_at'), 'ends_at')
        event.institution_id = _institution_id(data)
        if event.ends_at and event.ends_at < event.starts_at:
            raise ValueError('ends_at must be on or after starts_at.')
    except ValueError as exception:
        return jsonify({'error': str(exception)}), 400
    db.session.commit()
    return jsonify(_event_dict(event))


@campus_bp.route('/api/events/<int:event_id>', methods=['DELETE'])
def deactivate_event(event_id):
    event = Event.query.filter_by(id=event_id, active=True).first_or_404()
    data = request.get_json(silent=True) or {}
    if not verify_owner_token(event, data.get('owner_token')):
        return jsonify({'error': 'Valid owner token required.'}), 403
    event.active = False
    db.session.commit()
    return jsonify({'ok': True})


@campus_bp.route('/api/opportunities', methods=['GET'])
def list_opportunities():
    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(50, max(1, request.args.get('per_page', 20, type=int)))
    query = Opportunity.query.filter_by(active=True)
    opportunity_type = request.args.get('type', '').strip()
    if opportunity_type in {'job', 'internship', 'scholarship', 'attachment'}:
        query = query.filter_by(opportunity_type=opportunity_type)
    institution_id = request.args.get('institution_id', type=int)
    if institution_id:
        query = query.filter_by(institution_id=institution_id)
    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(db.or_(
            Opportunity.title.ilike(f'%{search}%'),
            Opportunity.organization.ilike(f'%{search}%'),
            Opportunity.description.ilike(f'%{search}%'),
        ))
    query = query.order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'items': [_opportunity_dict(item) for item in items],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page,
    })


@campus_bp.route('/api/opportunities', methods=['POST'])
@check_rate_limit(5, 3600)
def create_opportunity():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    try:
        opportunity_type = required_text(data, 'opportunity_type', 20)
        if opportunity_type not in {'job', 'internship', 'scholarship', 'attachment'}:
            raise ValueError('opportunity_type must be job, internship, scholarship, or attachment.')
        title = required_text(data, 'title', 200, 3)
        organization = required_text(data, 'organization', 200, 2)
        description = required_text(data, 'description', 5000, 5)
        location = optional_text(data, 'location', 200)
        application_url = optional_text(data, 'application_url', 500)
        if application_url and urlparse(application_url).scheme != 'https':
            raise ValueError('application_url must use HTTPS.')
        closes_at = _parse_datetime(data.get('closes_at'), 'closes_at')
        poster_name = required_text(data, 'poster_name', 100, 2)
        institution_id = _institution_id(data)
    except ValueError as exception:
        return jsonify({'error': str(exception)}), 400

    raw_idempotency_key = request.headers.get('Idempotency-Key')
    try:
        key_hash = idempotency_key_hash('opportunity', raw_idempotency_key)
    except ValueError as exception:
        return jsonify({'error': str(exception)}), 400
    existing = find_idempotent_record('opportunity', key_hash, Opportunity)
    if existing:
        response = _opportunity_dict(existing)
        response['owner_token'] = issue_owner_token('opportunity', raw_idempotency_key)[0]
        return jsonify(response), 200
    owner_token, owner_hash = issue_owner_token('opportunity', raw_idempotency_key)
    item = Opportunity(
        opportunity_type=opportunity_type, title=title, organization=organization,
        description=description, location=location or None,
        application_url=application_url or None, closes_at=closes_at,
        poster_name=poster_name, institution_id=institution_id,
        owner_token_hash=owner_hash,
    )
    db.session.add(item)
    try:
        remember_idempotent_record('opportunity', key_hash, item)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = find_idempotent_record('opportunity', key_hash, Opportunity)
        if not existing:
            raise
        response = _opportunity_dict(existing)
        response['owner_token'] = issue_owner_token('opportunity', raw_idempotency_key)[0]
        return jsonify(response), 200
    response = _opportunity_dict(item)
    response['owner_token'] = owner_token
    return jsonify(response), 201


@campus_bp.route('/api/opportunities/<int:item_id>', methods=['GET'])
def get_opportunity(item_id):
    item = Opportunity.query.filter_by(id=item_id, active=True).first_or_404()
    return jsonify(_opportunity_dict(item))


@campus_bp.route('/api/opportunities/<int:item_id>', methods=['PUT'])
def update_opportunity(item_id):
    item = Opportunity.query.filter_by(id=item_id, active=True).first_or_404()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    if not verify_owner_token(item, data.get('owner_token')):
        return jsonify({'error': 'Valid owner token required.'}), 403
    try:
        item.title = required_text(data, 'title', 200, 3)
        item.organization = required_text(data, 'organization', 200, 2)
        item.description = required_text(data, 'description', 5000, 5)
        item.location = optional_text(data, 'location', 200) or None
        item.application_url = optional_text(data, 'application_url', 500) or None
        if item.application_url and urlparse(item.application_url).scheme != 'https':
            raise ValueError('application_url must use HTTPS.')
        item.closes_at = _parse_datetime(data.get('closes_at'), 'closes_at')
        item.institution_id = _institution_id(data)
    except ValueError as exception:
        return jsonify({'error': str(exception)}), 400
    db.session.commit()
    return jsonify(_opportunity_dict(item))


@campus_bp.route('/api/opportunities/<int:item_id>', methods=['DELETE'])
def deactivate_opportunity(item_id):
    item = Opportunity.query.filter_by(id=item_id, active=True).first_or_404()
    data = request.get_json(silent=True) or {}
    if not verify_owner_token(item, data.get('owner_token')):
        return jsonify({'error': 'Valid owner token required.'}), 403
    item.active = False
    db.session.commit()
    return jsonify({'ok': True})


def _reaction_target(target_type, target_id):
    targets = {
        'post': Post,
        'institution_post': InstitutionPost,
        'event': Event,
        'opportunity': Opportunity,
    }
    model = targets.get(target_type)
    if not model:
        return None
    record = model.query.get(target_id)
    if not record or getattr(record, 'deleted', False) or not getattr(record, 'active', True):
        return None
    return record


@campus_bp.route('/api/reactions', methods=['POST'])
def create_reaction():
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account or not account.active:
        return jsonify({'error': 'Authentication required.'}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    target_type = data.get('target_type')
    try:
        target_id = int(data.get('target_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'target_id must be an integer.'}), 400
    reaction_type = data.get('reaction_type', 'like')
    if reaction_type not in {'like', 'celebrate', 'support'}:
        return jsonify({'error': 'Unsupported reaction type.'}), 400
    if not _reaction_target(target_type, target_id):
        return jsonify({'error': 'Target not found.'}), 404

    reaction = Reaction.query.filter_by(
        account_id=account.id, target_type=target_type, target_id=target_id
    ).first()
    if reaction:
        reaction.reaction_type = reaction_type
    else:
        reaction = Reaction(account_id=account.id, target_type=target_type,
                            target_id=target_id, reaction_type=reaction_type)
        db.session.add(reaction)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Reaction was already submitted.'}), 409
    return jsonify({'id': reaction.id, 'reaction_type': reaction.reaction_type}), 201


@campus_bp.route('/api/reactions/<string:target_type>/<int:target_id>', methods=['DELETE'])
def delete_reaction(target_type, target_id):
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account or not account.active:
        return jsonify({'error': 'Authentication required.'}), 401
    reaction = Reaction.query.filter_by(
        account_id=account.id, target_type=target_type, target_id=target_id
    ).first()
    if reaction:
        db.session.delete(reaction)
        db.session.commit()
    return jsonify({'ok': True})


@campus_bp.route('/api/notifications', methods=['GET'])
def list_notifications():
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account or not account.active:
        return jsonify({'error': 'Authentication required.'}), 401
    items = Notification.query.filter_by(account_id=account.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    return jsonify([{
        'id': item.id, 'title': item.title, 'body': item.body,
        'target_url': item.target_url,
        'read_at': item.read_at.isoformat() if item.read_at else None,
        'created_at': item.created_at.isoformat(),
    } for item in items])


@campus_bp.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    account = _get_account(request.headers.get('X-Account-Token'))
    if not account or not account.active:
        return jsonify({'error': 'Authentication required.'}), 401
    item = Notification.query.filter_by(
        id=notification_id, account_id=account.id
    ).first_or_404()
    item.read_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})
