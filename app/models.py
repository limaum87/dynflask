from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class DnsZone(db.Model):
    """Uma zona DNS (domínio) associada a um provider."""
    __tablename__ = 'dns_zones'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    provider = db.Column(db.String(50), nullable=False, default='cloudflare')
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    # Relationship
    hosts = db.relationship('Host', backref='zone', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def hosts_count(self):
        return self.hosts.count()

    @property
    def hosts_with_ip(self):
        return self.hosts.filter(Host.current_ip.isnot(None)).count()

    def __repr__(self):
        return f'<DnsZone {self.name} ({self.provider})>'


class Host(db.Model):
    """Um registro DNS dentro de uma zona."""
    __tablename__ = 'hosts'

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('dns_zones.id'), nullable=False)
    hostname = db.Column(db.String(255), nullable=False)
    record_type = db.Column(db.String(10), nullable=False, default='A')
    ttl = db.Column(db.Integer, nullable=False, default=300)
    auth_token = db.Column(db.String(255), nullable=False)
    current_ip = db.Column(db.String(45))
    last_updated = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<Host {self.hostname}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.Text)

    def __repr__(self):
        return f'<Setting {self.key}>'
