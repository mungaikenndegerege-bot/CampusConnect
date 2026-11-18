import uuid
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

class Account(db.Model):
    __tablename__ = 'account'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    sessions = db.relationship('AccountSession', backref='account', lazy=True)

class AccountSession(db.Model):
    __tablename__ = 'account_session'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    __tablename__ = 'report'
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(20), nullable=False)  # post/marketplace/lostandfound
    content_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    reporter_ip = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)


# --- Institution Directory Models ---

class InstitutionCategory(db.Model):
    __tablename__ = 'institution_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}


class Institution(db.Model):
    __tablename__ = 'institutions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    abbreviation = db.Column(db.String(20), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('institution_categories.id'))
    ownership = db.Column(db.String(10), default='Public')
    county = db.Column(db.String(100), nullable=True)
    town = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.relationship('InstitutionCategory', backref='institutions')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'abbreviation': self.abbreviation,
            'category': self.category.name if self.category else None,
            'category_id': self.category_id,
            'ownership': self.ownership, 'county': self.county,
            'town': self.town, 'website': self.website,
            'source': self.source, 'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InstitutionCommunity(db.Model):
    __tablename__ = 'institution_communities'
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), unique=True)
    member_count = db.Column(db.Integer, default=0)
    post_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    institution = db.relationship('Institution', backref=db.backref('community', uselist=False))

    def to_dict(self):
        return {
            'id': self.id, 'institution_id': self.institution_id,
            'member_count': self.member_count, 'post_count': self.post_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InstitutionPost(db.Model):
    __tablename__ = 'institution_posts'
    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'))
    community_id = db.Column(db.Integer, db.ForeignKey('institution_communities.id'))
    poster_name = db.Column(db.String(100), nullable=False)
    poster_contact = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(50), default='General')
    deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'institution_id': self.institution_id,
            'community_id': self.community_id,
            'poster_name': self.poster_name, 'poster_contact': self.poster_contact,
            'title': self.title, 'body': self.body, 'topic': self.topic,
            'deleted': self.deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InstitutionPostComment(db.Model):
    __tablename__ = 'institution_post_comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('institution_posts.id'))
    poster_name = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'post_id': self.post_id,
            'poster_name': self.poster_name, 'body': self.body,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
