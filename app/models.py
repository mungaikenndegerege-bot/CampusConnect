from datetime import datetime
from app import db

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    poster_name = db.Column(db.String(100), nullable=False)
    poster_contact = db.Column(db.String(100))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(50), default='General')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)
    comments = db.relationship('Comment', backref='post', lazy=True)

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    poster_name = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MarketplaceItem(db.Model):
    __tablename__ = 'marketplace_item'
    id = db.Column(db.Integer, primary_key=True)
    poster_name = db.Column(db.String(100), nullable=False)
    poster_contact = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(50))
    category = db.Column(db.String(50), default='Other')
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sold = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False)

class LostFoundItem(db.Model):
    __tablename__ = 'lost_found_item'
    id = db.Column(db.Integer, primary_key=True)
    poster_name = db.Column(db.String(100), nullable=False)
    poster_contact = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(10), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False)

class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pinned = db.Column(db.Boolean, default=False)

class Ad(db.Model):
    __tablename__ = 'ad'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255))
    link_url = db.Column(db.String(500))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)

class AdminSession(db.Model):
    __tablename__ = 'admin_session'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
