from collections import defaultdict
from datetime import datetime
from flask import request, jsonify
import threading

_lock = threading.Lock()
_hits = defaultdict(list)  # key: (ip, endpoint) -> list of timestamps

def check_rate_limit(max_requests, window_seconds):
    """Decorator factory. Returns a before_request-style decorator."""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or 'unknown'
            key = (ip, request.endpoint)
            now = datetime.utcnow().timestamp()
            with _lock:
                times = _hits[key]
                # Remove entries outside the window
                _hits[key] = [t for t in times if now - t < window_seconds]
                if len(_hits[key]) >= max_requests:
                    return jsonify({'error': 'Too many requests. Please wait before posting again.'}), 429
                _hits[key].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator
