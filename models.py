from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import uuid

def utcnow():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email         = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(512), nullable=False)
    full_name     = db.Column(db.String(255), nullable=False)
    is_verified   = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime(timezone=True), default=utcnow)
    last_login    = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active     = db.Column(db.Boolean, default=True)
    role          = db.Column(db.String(20), default='user')
    notes = db.relationship('NoteMetadata', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    otp   = db.relationship('OTPRecord', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class OTPRecord(db.Model):
    __tablename__ = 'otp_records'
    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    otp_hash   = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    attempts   = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def is_expired(self):
       now = datetime.now(timezone.utc)
       exp = self.expires_at
       if exp.tzinfo is None:
          from datetime import timezone as tz
          exp = exp.replace(tzinfo=timezone.utc)
       return now > exp
    
class NoteMetadata(db.Model):
    __tablename__ = 'note_metadata'
    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title      = db.Column(db.String(500), nullable=False)
    s3_key     = db.Column(db.String(500), nullable=False, unique=True)
    tags       = db.Column(db.String(1000), nullable=True)
    is_pinned  = db.Column(db.Boolean, default=False)
    word_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'tags': self.tags_list(),
            'is_pinned': self.is_pinned, 'word_count': self.word_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }