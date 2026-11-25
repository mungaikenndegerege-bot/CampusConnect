import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import Account, AccountSession, Conversation, Message
from app.ratelimit import check_rate_limit

messaging_bp = Blueprint('messaging_bp', __name__)

SESSION_DAYS = 30


def get_account_from_token(req):
    token = req.headers.get('X-Account-Token')
    if not token:
        return None
    cutoff = datetime.utcnow() - timedelta(days=SESSION_DAYS)
    s = AccountSession.query.filter(
        AccountSession.token == token,
        AccountSession.created_at >= cutoff
    ).first()
    if not s:
        return None
    account = s.account
    if not account or not account.active:
        return None
    return account


def _get_or_create_conversation(id_a, id_b):
    """Return existing conversation or create a new one. Always stores participant_a_id < participant_b_id."""
    lo, hi = (id_a, id_b) if id_a < id_b else (id_b, id_a)
    conv = Conversation.query.filter_by(participant_a_id=lo, participant_b_id=hi).first()
    if conv:
        return conv, False
    conv = Conversation(participant_a_id=lo, participant_b_id=hi)
    db.session.add(conv)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        conv = Conversation.query.filter_by(participant_a_id=lo, participant_b_id=hi).first()
        return conv, False
    return conv, True


@messaging_bp.route('/api/messages/conversations', methods=['GET'])
def list_conversations():
    account = get_account_from_token(request)
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    convs = Conversation.query.filter(
        db.or_(
            Conversation.participant_a_id == account.id,
            Conversation.participant_b_id == account.id
        )
    ).order_by(Conversation.last_message_at.desc()).all()
    result = []
    for c in convs:
        d = c.to_dict(current_account_id=account.id)
        # Attach last message preview and unread count
        last_msg = Message.query.filter_by(conversation_id=c.id)\
            .order_by(Message.created_at.desc()).first()
        d['last_message_preview'] = (last_msg.body[:80] if last_msg else '')
        d['unread_count'] = Message.query.filter(
            Message.conversation_id == c.id,
            Message.sender_id != account.id,
            Message.read_at.is_(None)
        ).count()
        result.append(d)
    return jsonify(result)


@messaging_bp.route('/api/messages/conversations', methods=['POST'])
def create_conversation():
    account = get_account_from_token(request)
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    recipient_id = d.get('recipient_id')
    if not isinstance(recipient_id, int):
        return jsonify({'error': 'recipient_id must be an integer.'}), 400
    if recipient_id == account.id:
        return jsonify({'error': 'Cannot message yourself.'}), 400
    recipient = Account.query.filter_by(id=recipient_id, active=True).first()
    if not recipient:
        return jsonify({'error': 'Recipient not found.'}), 404
    conv, created = _get_or_create_conversation(account.id, recipient_id)
    db.session.commit()
    status = 201 if created else 200
    return jsonify(conv.to_dict(current_account_id=account.id)), status


@messaging_bp.route('/api/messages/conversations/<int:conv_id>', methods=['GET'])
def get_conversation(conv_id):
    account = get_account_from_token(request)
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    conv = Conversation.query.get_or_404(conv_id)
    if account.id not in (conv.participant_a_id, conv.participant_b_id):
        return jsonify({'error': 'Forbidden'}), 403
    page = request.args.get('page', 1, type=int)
    per_page = 30
    msgs_q = Message.query.filter_by(conversation_id=conv_id)\
        .order_by(Message.created_at.desc())
    total = msgs_q.count()
    msgs = msgs_q.offset((page - 1) * per_page).limit(per_page).all()
    msgs.reverse()
    return jsonify({
        'conversation': conv.to_dict(current_account_id=account.id),
        'messages': [m.to_dict() for m in msgs],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page,
    })


@messaging_bp.route('/api/messages/conversations/<int:conv_id>', methods=['POST'])
@check_rate_limit(30, 3600)
def send_message(conv_id):
    account = get_account_from_token(request)
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    conv = Conversation.query.get_or_404(conv_id)
    if account.id not in (conv.participant_a_id, conv.participant_b_id):
        return jsonify({'error': 'Forbidden'}), 403
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        return jsonify({'error': 'A JSON object is required.'}), 400
    body = d.get('body', '').strip()
    if not body:
        return jsonify({'error': 'Message body is required.'}), 400
    if len(body) > 2000:
        return jsonify({'error': 'Message too long (max 2000 characters).'}), 400
    msg = Message(conversation_id=conv_id, sender_id=account.id, body=body)
    conv.last_message_at = datetime.utcnow()
    db.session.add(msg)
    db.session.commit()
    return jsonify(msg.to_dict()), 201


@messaging_bp.route('/api/messages/conversations/<int:conv_id>/read', methods=['PUT'])
def mark_read(conv_id):
    account = get_account_from_token(request)
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    conv = Conversation.query.get_or_404(conv_id)
    if account.id not in (conv.participant_a_id, conv.participant_b_id):
        return jsonify({'error': 'Forbidden'}), 403
    now = datetime.utcnow()
    Message.query.filter(
        Message.conversation_id == conv_id,
        Message.sender_id != account.id,
        Message.read_at.is_(None)
    ).update({'read_at': now}, synchronize_session=False)
    db.session.commit()
    return jsonify({'ok': True})


@messaging_bp.route('/api/messages/unread-count', methods=['GET'])
def unread_count():
    account = get_account_from_token(request)
    if not account:
        return jsonify({'error': 'Unauthorized'}), 401
    conv_ids = db.session.query(Conversation.id).filter(
        db.or_(
            Conversation.participant_a_id == account.id,
            Conversation.participant_b_id == account.id
        )
    ).subquery()
    count = Message.query.filter(
        Message.conversation_id.in_(conv_ids),
        Message.sender_id != account.id,
        Message.read_at.is_(None)
    ).count()
    return jsonify({'count': count})
