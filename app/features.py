import hashlib
import hmac
import ipaddress
import json
import os
from datetime import date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import Blueprint, abort, current_app, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import AdminSession, FeaturePost, FeatureVote
from app.ratelimit import check_rate_limit

features_bp = Blueprint('features_bp', __name__)

FEATURE_KINDS = {
    'jobs', 'accommodation', 'resources', 'deals', 'events',
    'polls', 'confessions', 'lost_documents', 'services',
}
TEXT_LIMITS = {
    'title': 160,
    'body': 4000,
    'author_name': 100,
    'contact': 160,
    'location': 160,
    'price': 80,
    'category': 80,
    'external_url': 500,
}


def _clean(value):
    return value.strip() if isinstance(value, str) else ''


def _serialize_feature(item, poll_counts=None):
    try:
        options = json.loads(item.poll_options) if item.poll_options else []
    except (TypeError, ValueError):
        options = []
    result = {
        'id': item.id,
        'kind': item.kind,
        'title': item.title,
        'body': item.body,
        'author_name': 'Anonymous' if item.kind == 'confessions' else item.author_name,
        'location': item.location,
        'price': item.price,
        'category': item.category,
        'event_date': item.event_date,
        'deadline': item.deadline,
        'external_url': item.external_url,
        'anonymous': item.kind == 'confessions',
        'created_at': item.created_at.isoformat() if item.created_at else None,
    }
    if item.kind != 'lost_documents':
        result['contact'] = item.contact
    if item.kind == 'polls':
        result['options'] = options
        result['counts'] = poll_counts or [0] * len(options)
    return result


def _poll_counts(feature_ids):
    rows = db.session.query(
        FeatureVote.feature_id,
        FeatureVote.option_index,
        func.count(FeatureVote.id)
    ).filter(FeatureVote.feature_id.in_(feature_ids)).group_by(
        FeatureVote.feature_id, FeatureVote.option_index
    ).all()
    counts = {}
    for feature_id, option_index, count in rows:
        counts.setdefault(feature_id, {})[option_index] = count
    return counts


def _valid_date(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f'{field_name} must be a valid YYYY-MM-DD date.')


def _valid_url(value):
    if not value:
        return ''
    parts = urlsplit(value)
    if parts.scheme not in ('http', 'https') or not parts.netloc or parts.username or parts.password:
        raise ValueError('Enter a valid http:// or https:// link.')
    return value


@features_bp.route('/api/features', methods=['GET'])
def list_features():
    kind = _clean(request.args.get('kind'))
    if kind not in FEATURE_KINDS:
        return jsonify({'error': 'Choose a valid feature category.'}), 400
    query = FeaturePost.query.filter_by(kind=kind, active=True)
    if kind == 'events':
        query = query.filter(FeaturePost.event_date >= date.today().isoformat())
        query = query.order_by(FeaturePost.event_date.asc())
    else:
        query = query.order_by(FeaturePost.created_at.desc())
    items = query.limit(50).all()
    counts_by_feature = _poll_counts([item.id for item in items if item.kind == 'polls'])
    result = []
    for item in items:
        counts = counts_by_feature.get(item.id, {})
        options = json.loads(item.poll_options) if item.poll_options else []
        result.append(_serialize_feature(item, [counts.get(index, 0) for index in range(len(options))]))
    return jsonify({'items': result})


@features_bp.route('/api/features', methods=['POST'])
@check_rate_limit(12, 3600)
def create_feature():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Send a valid JSON request.'}), 400
    kind = _clean(data.get('kind'))
    if kind not in FEATURE_KINDS:
        return jsonify({'error': 'Choose a valid feature category.'}), 400

    fields = {name: _clean(data.get(name)) for name in TEXT_LIMITS}
    for name, maximum in TEXT_LIMITS.items():
        if len(fields[name]) > maximum:
            return jsonify({'error': f'{name.replace("_", " ").title()} must be {maximum} characters or fewer.'}), 400
    if not fields['title'] or not fields['body']:
        return jsonify({'error': 'A title and description are required.'}), 400
    if kind not in ('confessions', 'polls', 'lost_documents') and len(fields['author_name']) < 2:
        return jsonify({'error': 'Enter a name to publish this listing.'}), 400
    if kind in ('confessions', 'polls', 'lost_documents'):
        fields['contact'] = ''
    if kind == 'lost_documents':
        fields['author_name'] = fields['author_name'] or 'CampusConnect community'
    if kind == 'confessions':
        fields['author_name'] = 'Anonymous'

    try:
        fields['external_url'] = _valid_url(fields['external_url'])
        event_date = _valid_date(_clean(data.get('event_date')), 'Event date')
        deadline = _valid_date(_clean(data.get('deadline')), 'Deadline')
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    if kind == 'events' and not event_date:
        return jsonify({'error': 'Choose the date of the event.'}), 400

    options = []
    if kind == 'polls':
        raw_options = data.get('options')
        if not isinstance(raw_options, list):
            return jsonify({'error': 'Add two to six poll choices.'}), 400
        options = [_clean(option) for option in raw_options]
        if not 2 <= len(options) <= 6 or any(not option or len(option) > 80 for option in options):
            return jsonify({'error': 'Polls need two to six choices, each no longer than 80 characters.'}), 400
        if len({option.casefold() for option in options}) != len(options):
            return jsonify({'error': 'Poll choices must be unique.'}), 400

    item = FeaturePost(
        kind=kind,
        title=fields['title'],
        body=fields['body'],
        author_name=fields['author_name'] or 'CampusConnect community',
        contact=fields['contact'] or None,
        location=fields['location'] or None,
        price=fields['price'] or None,
        category=fields['category'] or None,
        event_date=event_date,
        deadline=deadline,
        external_url=fields['external_url'] or None,
        poll_options=json.dumps(options) if options else None,
        anonymous=kind == 'confessions',
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(_serialize_feature(item, [0] * len(options))), 201


@features_bp.route('/api/features/<int:feature_id>/vote', methods=['POST'])
@check_rate_limit(30, 3600)
def vote_feature_poll(feature_id):
    item = FeaturePost.query.filter_by(id=feature_id, kind='polls', active=True).first_or_404()
    data = request.get_json(silent=True) or {}
    voter_key = _clean(data.get('voter_key'))
    option_index = data.get('option_index')
    options = json.loads(item.poll_options or '[]')
    if not isinstance(option_index, int) or isinstance(option_index, bool) or not 0 <= option_index < len(options):
        return jsonify({'error': 'Choose one of the poll options.'}), 400
    if not 16 <= len(voter_key) <= 128:
        return jsonify({'error': 'Refresh the page and try voting again.'}), 400

    secret = current_app.config.get('SECRET_KEY') or 'campusconnect-poll-vote'
    voter_hash = hmac.new(str(secret).encode(), voter_key.encode(), hashlib.sha256).hexdigest()
    db.session.add(FeatureVote(
        feature_id=item.id, voter_hash=voter_hash, option_index=option_index
    ))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'You have already voted in this poll.'}), 409

    counts = _poll_counts([item.id]).get(item.id, {})
    return jsonify({
        'options': options,
        'counts': [counts.get(index, 0) for index in range(len(options))],
    })


def _admin_authorized():
    token = request.headers.get('X-Admin-Token', '')
    if not token.startswith('v2_'):
        return False
    cutoff = datetime.utcnow() - timedelta(hours=24)
    return AdminSession.query.filter(
        AdminSession.token == token,
        AdminSession.created_at >= cutoff
    ).first() is not None


@features_bp.route('/api/admin/features', methods=['GET'])
def admin_list_features():
    if not _admin_authorized():
        return jsonify({'error': 'Unauthorized'}), 401
    items = FeaturePost.query.order_by(FeaturePost.created_at.desc()).limit(200).all()
    counts_by_feature = _poll_counts([item.id for item in items if item.kind == 'polls'])
    result = []
    for item in items:
        options = json.loads(item.poll_options) if item.poll_options else []
        counts = counts_by_feature.get(item.id, {})
        result.append(_serialize_feature(item, [counts.get(index, 0) for index in range(len(options))]))
    return jsonify({'items': result})


@features_bp.route('/api/admin/features/<int:feature_id>', methods=['DELETE'])
def admin_delete_feature(feature_id):
    if not _admin_authorized():
        return jsonify({'error': 'Unauthorized'}), 401
    item = db.session.get(FeaturePost, feature_id)
    if item is None:
        abort(404)
    item.active = False
    db.session.commit()
    return jsonify({'ok': True})


@features_bp.route('/api/study-assistant', methods=['POST'])
@check_rate_limit(5, 300)
def study_assistant():
    data = request.get_json(silent=True) or {}
    question = _clean(data.get('question'))
    if not question or len(question) > 4000:
        return jsonify({'error': 'Enter a study question up to 4,000 characters.'}), 400

    api_key = current_app.config.get('AI_API_KEY') or os.environ.get('AI_API_KEY')
    if not api_key:
        return jsonify({'error': 'The Study Assistant is not configured yet. Please try again later.'}), 503

    base_url = (
        current_app.config.get('AI_API_BASE_URL')
        or os.environ.get('AI_API_BASE_URL')
        or 'https://api.openai.com/v1'
    ).rstrip('/')
    parts = urlsplit(base_url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        current_app.logger.error('AI_API_BASE_URL must be an HTTPS URL without embedded credentials.')
        return jsonify({'error': 'The Study Assistant provider configuration is invalid.'}), 503
    try:
        address = ipaddress.ip_address(parts.hostname)
        if not address.is_global:
            current_app.logger.error('AI_API_BASE_URL cannot point to a private or local address.')
            return jsonify({'error': 'The Study Assistant provider configuration is invalid.'}), 503
    except ValueError:
        if parts.hostname.lower() == 'localhost' or parts.hostname.lower().endswith(('.localhost', '.local', '.internal')):
            current_app.logger.error('AI_API_BASE_URL cannot point to a local hostname.')
            return jsonify({'error': 'The Study Assistant provider configuration is invalid.'}), 503

    payload = {
        'model': current_app.config.get('AI_MODEL') or os.environ.get('AI_MODEL') or 'gpt-4o-mini',
        'messages': [
            {
                'role': 'system',
                'content': (
                    'You are CampusConnect Study Assistant, a supportive tutor. Explain ideas clearly '
                    'in steps, ask a short check-for-understanding question when helpful, and encourage '
                    'learning rather than completing dishonest exam submissions. State uncertainty and '
                    'never invent sources.'
                ),
            },
            {'role': 'user', 'content': question},
        ],
        'temperature': 0.4,
        'max_tokens': 900,
    }
    outgoing = Request(
        f'{base_url}/chat/completions',
        data=json.dumps(payload).encode(),
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(outgoing, timeout=25) as response:
            provider_data = json.loads(response.read(1024 * 1024))
        answer = provider_data['choices'][0]['message']['content'].strip()
        if not answer:
            raise ValueError('The AI provider returned an empty answer.')
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError):
        current_app.logger.exception('Study Assistant provider request failed.')
        return jsonify({'error': 'The Study Assistant could not answer right now. Please try again later.'}), 502

    return jsonify({'answer': answer[:12000]})
