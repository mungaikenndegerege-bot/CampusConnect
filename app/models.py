import uuid
from datetime import datetime, date
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(300), nullable=True)
    file_type = db.Column(db.String(20), nullable=True)
    owner_token_hash = db.Column(db.String(64), nullable=True, index=True)
    comments = db.relationship('Comment', backref='post', lazy=True)
    __table_args__ = (
        db.Index('ix_post_visible_created', 'deleted', 'created_at'),
    )

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    poster_name = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id', ondelete='CASCADE'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side='Comment.id'), lazy=True)
    __table_args__ = (db.Index('ix_comment_post_created', 'post_id', 'created_at'),)

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
    owner_token_hash = db.Column(db.String(64), nullable=True, index=True)
    __table_args__ = (
        db.Index('ix_marketplace_visible_created', 'deleted', 'sold', 'created_at'),
    )

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
    owner_token_hash = db.Column(db.String(64), nullable=True, index=True)
    __table_args__ = (
        db.Index('ix_lost_found_visible_created', 'deleted', 'resolved', 'created_at'),
    )

class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    pinned = db.Column(db.Boolean, default=False)
    __table_args__ = (
        db.Index('ix_announcement_pinned_created', 'pinned', 'created_at'),
    )

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
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=True)
    institution = db.relationship('Institution', foreign_keys=[institution_id])
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
    __table_args__ = (db.Index('ix_institution_active_name', 'active', 'name'),)

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
    file_path = db.Column(db.String(300), nullable=True)
    file_type = db.Column(db.String(20), nullable=True)
    owner_token_hash = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        from app.storage import asset_url
        return {
            'id': self.id, 'institution_id': self.institution_id,
            'community_id': self.community_id,
            'poster_name': self.poster_name, 'poster_contact': self.poster_contact,
            'title': self.title, 'body': self.body, 'topic': self.topic,
            'deleted': self.deleted,
            'file_url': asset_url(self.file_path),
            'file_type': self.file_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InstitutionPostComment(db.Model):
    __tablename__ = 'institution_post_comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('institution_posts.id'))
    poster_name = db.Column(db.String(100))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'post_id': self.post_id,
            'poster_name': self.poster_name, 'body': self.body,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# --- Advertiser System Models ---

class Advertiser(db.Model):
    __tablename__ = 'advertisers'
    id            = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(200), nullable=False)
    contact_name  = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    phone         = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    website       = db.Column(db.String(200), nullable=True)
    description   = db.Column(db.Text, nullable=True)
    status        = db.Column(db.String(20), default='pending')
    approved_at   = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'business_name': self.business_name,
            'contact_name': self.contact_name, 'email': self.email,
            'phone': self.phone, 'website': self.website,
            'description': self.description, 'status': self.status,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AdvertiserSession(db.Model):
    __tablename__ = 'advertiser_sessions'
    id            = db.Column(db.Integer, primary_key=True)
    advertiser_id = db.Column(db.Integer, db.ForeignKey('advertisers.id'))
    token         = db.Column(db.String(64), unique=True, index=True, nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    advertiser    = db.relationship('Advertiser', backref='sessions')

    def to_dict(self):
        return {'id': self.id, 'advertiser_id': self.advertiser_id,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class AdPlacement(db.Model):
    __tablename__ = 'ad_placements'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    description   = db.Column(db.Text, nullable=True)
    price_per_day = db.Column(db.Float, default=0.0)
    active        = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description,
                'price_per_day': self.price_per_day, 'active': self.active}


class AdCampaign(db.Model):
    __tablename__ = 'ad_campaigns'
    id             = db.Column(db.Integer, primary_key=True)
    advertiser_id  = db.Column(db.Integer, db.ForeignKey('advertisers.id'))
    name           = db.Column(db.String(200), nullable=False)
    start_date     = db.Column(db.Date, nullable=False)
    end_date       = db.Column(db.Date, nullable=False)
    status         = db.Column(db.String(20), default='pending')
    total_budget   = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='unpaid')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    advertiser     = db.relationship('Advertiser', backref='campaigns')

    def to_dict(self):
        return {
            'id': self.id, 'advertiser_id': self.advertiser_id,
            'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status, 'total_budget': self.total_budget,
            'payment_status': self.payment_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Advertisement(db.Model):
    __tablename__ = 'advertisements'
    id           = db.Column(db.Integer, primary_key=True)
    campaign_id  = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    placement_id = db.Column(db.Integer, db.ForeignKey('ad_placements.id'))
    title        = db.Column(db.String(200), nullable=False)
    body         = db.Column(db.Text, nullable=True)
    image_path   = db.Column(db.String(300), nullable=True)
    link_url     = db.Column(db.String(500), nullable=True)
    status       = db.Column(db.String(20), default='pending')
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    campaign     = db.relationship('AdCampaign', backref='advertisements')
    placement    = db.relationship('AdPlacement', backref='advertisements')

    def to_dict(self):
        from app.storage import asset_url
        return {
            'id': self.id, 'campaign_id': self.campaign_id,
            'placement_id': self.placement_id,
            'title': self.title, 'body': self.body,
            'image_path': asset_url(self.image_path), 'link_url': self.link_url,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AdImpression(db.Model):
    __tablename__ = 'ad_impressions'
    id               = db.Column(db.Integer, primary_key=True)
    advertisement_id = db.Column(db.Integer, db.ForeignKey('advertisements.id'))
    campaign_id      = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    visitor_hash     = db.Column(db.String(64), nullable=True)
    placement        = db.Column(db.String(100), nullable=True)
    recorded_at      = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__   = (db.Index('ix_imp_ad_date', 'advertisement_id', 'recorded_at'),)

    def to_dict(self):
        return {'id': self.id, 'advertisement_id': self.advertisement_id,
                'campaign_id': self.campaign_id, 'placement': self.placement,
                'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None}


class AdClick(db.Model):
    __tablename__ = 'ad_clicks'
    id               = db.Column(db.Integer, primary_key=True)
    advertisement_id = db.Column(db.Integer, db.ForeignKey('advertisements.id'))
    campaign_id      = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    visitor_hash     = db.Column(db.String(64), nullable=True)
    placement        = db.Column(db.String(100), nullable=True)
    destination_url  = db.Column(db.String(500), nullable=True)
    recorded_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'advertisement_id': self.advertisement_id,
                'campaign_id': self.campaign_id, 'placement': self.placement,
                'destination_url': self.destination_url,
                'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None}


class AdDailyStat(db.Model):
    __tablename__ = 'ad_daily_stats'
    id               = db.Column(db.Integer, primary_key=True)
    advertisement_id = db.Column(db.Integer, db.ForeignKey('advertisements.id'))
    campaign_id      = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    date             = db.Column(db.Date, nullable=False)
    impressions      = db.Column(db.Integer, default=0)
    unique_reach     = db.Column(db.Integer, default=0)
    clicks           = db.Column(db.Integer, default=0)
    __table_args__   = (
        db.UniqueConstraint('advertisement_id', 'date', name='uq_ad_daily'),
        db.Index('ix_adstat_campaign_date', 'campaign_id', 'date'),
    )

    def to_dict(self):
        return {
            'id': self.id, 'advertisement_id': self.advertisement_id,
            'campaign_id': self.campaign_id,
            'date': self.date.isoformat() if self.date else None,
            'impressions': self.impressions, 'unique_reach': self.unique_reach,
            'clicks': self.clicks
        }


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=True, index=True)
    venue = db.Column(db.String(200), nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    poster_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=True)
    poster_path = db.Column(db.String(300), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_token_hash = db.Column(db.String(64), nullable=True, index=True)
    institution = db.relationship('Institution')
    __table_args__ = (db.Index('ix_event_active_starts', 'active', 'starts_at'),)


class Opportunity(db.Model):
    __tablename__ = 'opportunities'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_type = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=True)
    application_url = db.Column(db.String(500), nullable=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.id'), nullable=True, index=True)
    closes_at = db.Column(db.DateTime, nullable=True, index=True)
    poster_name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_token_hash = db.Column(db.String(64), nullable=True, index=True)
    institution = db.relationship('Institution')
    __table_args__ = (
        db.Index('ix_opportunity_active_created', 'active', 'created_at'),
    )


class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False, index=True)
    target_type = db.Column(db.String(30), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False, default='like')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    account = db.relationship('Account')
    __table_args__ = (
        db.UniqueConstraint('account_id', 'target_type', 'target_id', name='uq_reaction_account_target'),
        db.CheckConstraint("target_type IN ('post', 'institution_post', 'event', 'opportunity')",
                           name='ck_reaction_target_type'),
        db.CheckConstraint("reaction_type IN ('like', 'celebrate', 'support')",
                           name='ck_reaction_type'),
    )


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    target_url = db.Column(db.String(500), nullable=True)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    account = db.relationship('Account')


class IdempotencyRecord(db.Model):
    __tablename__ = 'idempotency_records'
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(40), nullable=False)
    key_hash = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    __table_args__ = (
        db.UniqueConstraint('resource_type', 'key_hash', name='uq_idempotency_resource_key'),
        db.Index('ix_idempotency_resource', 'resource_type', 'resource_id'),
    )


class AdPayment(db.Model):
    __tablename__ = 'ad_payments'
    id             = db.Column(db.Integer, primary_key=True)
    campaign_id    = db.Column(db.Integer, db.ForeignKey('ad_campaigns.id'))
    amount         = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    reference      = db.Column(db.String(100), nullable=True)
    status         = db.Column(db.String(20), default='pending')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at   = db.Column(db.DateTime, nullable=True)
    campaign       = db.relationship('AdCampaign', backref=db.backref('payment', uselist=False))

    def to_dict(self):
        return {
            'id': self.id, 'campaign_id': self.campaign_id,
            'amount': self.amount, 'payment_method': self.payment_method,
            'reference': self.reference, 'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None
        }


class FeaturePost(db.Model):
    __tablename__ = 'feature_posts'
    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(32), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), nullable=False, default='CampusConnect community')
    contact = db.Column(db.String(160))
    location = db.Column(db.String(160))
    price = db.Column(db.String(80))
    category = db.Column(db.String(80))
    event_date = db.Column(db.String(32))
    deadline = db.Column(db.String(32))
    external_url = db.Column(db.String(500))
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))
    poll_options = db.Column(db.Text)
    anonymous = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class FeatureVote(db.Model):
    __tablename__ = 'feature_votes'
    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.Integer, db.ForeignKey('feature_posts.id'), nullable=False, index=True)
    voter_hash = db.Column(db.String(64), nullable=False)
    option_index = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('feature_id', 'voter_hash', name='uq_feature_vote_voter'),
    )
