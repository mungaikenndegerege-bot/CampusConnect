import os
from flask import Flask, jsonify, redirect, render_template, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.storage import StorageError, StorageValidationError, resolve_asset

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_overrides=None):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object('config.Config')
    if config_overrides:
        app.config.update(config_overrides)
    production = os.environ.get('FLASK_ENV', '').lower() == 'production'
    if not app.config['SECRET_KEY']:
        if production:
            raise RuntimeError('SECRET_KEY must be configured in production.')
        app.config['SECRET_KEY'] = os.urandom(32).hex()
    if app.config['STORAGE_BACKEND'] == 'supabase':
        if not app.config['SUPABASE_URL'] or not app.config['SUPABASE_SERVICE_ROLE_KEY']:
            raise RuntimeError('SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase Storage.')
    elif app.config['STORAGE_BACKEND'] != 'local':
        raise RuntimeError('STORAGE_BACKEND must be either local or supabase.')

    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    database_driver = getattr(database_uri, 'drivername', str(database_uri).split(':', 1)[0])
    if database_driver.startswith('postgresql'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 5,
            'max_overflow': 5,
        }
    if app.config['CORS_ORIGINS']:
        CORS(app, origins=app.config['CORS_ORIGINS'])
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    from app.public import public_bp
    from app.admin import admin_bp
    from app.accounts import accounts_bp
    from app.features import features_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(features_bp)
    from app.institutions import institutions_bp, admin_inst_bp
    app.register_blueprint(institutions_bp)
    app.register_blueprint(admin_inst_bp)

    from app.advertiser import advertiser_bp
    app.register_blueprint(advertiser_bp)

    from app.ad_tracking import tracking_bp
    app.register_blueprint(tracking_bp)
    from app.campus import campus_bp
    app.register_blueprint(campus_bp)

    from app.messaging import messaging_bp
    app.register_blueprint(messaging_bp)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.errorhandler(StorageError)
    def handle_storage_error(exception):
        app.logger.warning('Storage operation failed: %s', exception)
        status = 400 if isinstance(exception, StorageValidationError) else 503
        return jsonify({'error': str(exception)}), status

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(exception):
        db.session.rollback()
        app.logger.error(
            'Database operation failed: %s',
            exception,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Database operation failed. Please try again.'}), 503
        return 'Service temporarily unavailable.', 503

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/health')
    def health():
        try:
            db.session.execute(text('SELECT 1'))
        except Exception:
            app.logger.exception('Health check database query failed')
            return jsonify({'status': 'unavailable'}), 503
        return jsonify({'status': 'ok'})

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if request_is_secure():
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    @app.route('/api/uploads/<path:filename>')
    def serve_upload(filename):
        if filename.startswith('sb://'):
            destination = resolve_asset(filename)
            if not destination:
                return jsonify({'error': 'File not found'}), 404
            return redirect(destination, code=302)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    @app.route('/admin')
    def admin_view():
        return render_template('admin.html')

    @app.route('/advertiser')
    @app.route('/advertiser/')
    def advertiser_portal():
        return render_template('advertiser.html')

    return app


def request_is_secure():
    from flask import request
    return request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https'
