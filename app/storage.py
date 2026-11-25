import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app
from werkzeug.utils import secure_filename


class StorageError(Exception):
    pass


class StorageValidationError(StorageError):
    pass


BUCKETS = {
    'profile': ('profile-pictures', False),
    'post_image': ('post-images', True),
    'event_poster': ('event-posters', True),
    'document': ('documents', False),
    'advertisement': ('advertisements', True),
    'institution_logo': ('institution-logos', True),
}

MIME_TYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif',
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def _validate_signature(extension, content):
    signatures = {
        'jpg': content.startswith(b'\xff\xd8\xff'),
        'jpeg': content.startswith(b'\xff\xd8\xff'),
        'png': content.startswith(b'\x89PNG\r\n\x1a\n'),
        'webp': len(content) >= 12 and content.startswith(b'RIFF') and content[8:12] == b'WEBP',
        'gif': content.startswith((b'GIF87a', b'GIF89a')),
        'pdf': content.startswith(b'%PDF-'),
        'docx': content.startswith(b'PK\x03\x04'),
        'doc': content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'),
    }
    return signatures.get(extension, False)


def upload_asset(file, category, max_bytes, allowed_extensions):
    if category not in BUCKETS:
        raise StorageValidationError('Unsupported upload category.')
    if not file or not file.filename:
        return None

    safe_name = secure_filename(file.filename)
    if '.' not in safe_name:
        raise StorageValidationError('The uploaded file must have a supported extension.')
    extension = safe_name.rsplit('.', 1)[1].lower()
    if extension not in allowed_extensions or extension not in MIME_TYPES:
        raise StorageValidationError('This file type is not allowed.')

    content = file.stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise StorageValidationError('The uploaded file exceeds the size limit.')
    if not _validate_signature(extension, content):
        raise StorageValidationError('The file contents do not match its extension.')

    bucket, _is_public = BUCKETS[category]
    object_name = f'{secrets.token_hex(16)}.{extension}'
    if current_app.config['STORAGE_BACKEND'] == 'supabase':
        return _upload_supabase(bucket, object_name, content, MIME_TYPES[extension])
    if current_app.config['STORAGE_BACKEND'] != 'local':
        raise StorageError('STORAGE_BACKEND must be either local or supabase.')

    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
    local_path = os.path.join(current_app.config['UPLOAD_FOLDER'], object_name)
    try:
        with open(local_path, 'xb') as destination:
            destination.write(content)
    except OSError as exception:
        raise StorageError('Could not save the uploaded file.') from exception
    return object_name


def delete_asset(reference):
    if not reference:
        return
    if reference.startswith('sb://'):
        parsed = urllib.parse.urlsplit(reference)
        bucket = parsed.netloc
        object_name = parsed.path.lstrip('/')
        if bucket not in {details[0] for details in BUCKETS.values()}:
            raise StorageError('Unknown storage bucket.')
        encoded_name = urllib.parse.quote(object_name, safe='/')
        _request('DELETE', f'object/{urllib.parse.quote(bucket, safe="")}/{encoded_name}')
        return
    local_path = os.path.join(current_app.config['UPLOAD_FOLDER'], reference)
    if os.path.isfile(local_path):
        os.remove(local_path)


def asset_url(reference):
    if not reference:
        return None
    if reference.startswith(('https://', 'http://')):
        return reference
    return '/api/uploads/' + urllib.parse.quote(reference, safe='')


def resolve_asset(reference):
    if reference.startswith('sb://'):
        parsed = urllib.parse.urlsplit(reference)
        bucket = parsed.netloc
        object_name = parsed.path.lstrip('/')
        if bucket not in {details[0] for details in BUCKETS.values()}:
            raise StorageError('Unknown storage bucket.')
        bucket_is_public = next(public for name, public in BUCKETS.values() if name == bucket)
        if bucket_is_public:
            return _public_url(bucket, object_name)
        return _signed_url(bucket, object_name)
    return None


def _supabase_config():
    base_url = current_app.config['SUPABASE_URL']
    service_key = current_app.config['SUPABASE_SERVICE_ROLE_KEY']
    if not base_url or not service_key:
        raise StorageError('Supabase Storage is selected but its server credentials are not configured.')
    return base_url, service_key


def _request(method, endpoint, body=None, content_type=None):
    base_url, service_key = _supabase_config()
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
    }
    if content_type:
        headers['Content-Type'] = content_type
    if body is not None and content_type == 'application/json':
        body = json.dumps(body).encode('utf-8')
    request = urllib.request.Request(
        f'{base_url}/storage/v1/{endpoint}',
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read()
            return json.loads(response_body) if response_body else {}
    except (urllib.error.URLError, TimeoutError, ValueError) as exception:
        raise StorageError('Supabase Storage request failed.') from exception


def _upload_supabase(bucket, object_name, content, content_type):
    encoded_bucket = urllib.parse.quote(bucket, safe='')
    encoded_name = urllib.parse.quote(object_name, safe='/')
    _request(
        'POST',
        f'object/{encoded_bucket}/{encoded_name}',
        body=content,
        content_type=content_type,
    )
    return f'sb://{bucket}/{object_name}'


def _public_url(bucket, object_name):
    base_url, _service_key = _supabase_config()
    return (
        f'{base_url}/storage/v1/object/public/'
        f'{urllib.parse.quote(bucket, safe="")}/{urllib.parse.quote(object_name, safe="/")}'
    )


def _signed_url(bucket, object_name):
    response = _request(
        'POST',
        f'object/sign/{urllib.parse.quote(bucket, safe="")}/{urllib.parse.quote(object_name, safe="/")}',
        body={'expiresIn': 3600},
        content_type='application/json',
    )
    signed_path = response.get('signedURL')
    if not signed_path:
        raise StorageError('Supabase did not return a signed download URL.')
    base_url, _service_key = _supabase_config()
    return urllib.parse.urljoin(f'{base_url}/storage/v1/', signed_path.lstrip('/'))
