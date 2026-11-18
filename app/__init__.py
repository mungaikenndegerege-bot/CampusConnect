import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object('config.Config')
    db.init_app(app)
    CORS(app)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    from app.public import public_bp
    from app.admin import admin_bp
    from app.accounts import accounts_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(accounts_bp)
    from app.institutions import institutions_bp, admin_inst_bp
    app.register_blueprint(institutions_bp)
    app.register_blueprint(admin_inst_bp)

    from app.advertiser import advertiser_bp
    app.register_blueprint(advertiser_bp)

    from app.ad_tracking import tracking_bp
    app.register_blueprint(tracking_bp)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/admin')
    def admin_view():
        return render_template('admin.html')

    @app.route('/advertiser')
    @app.route('/advertiser/')
    def advertiser_portal():
        return render_template('advertiser.html')

    return app
