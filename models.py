from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    locked_until = db.Column(db.DateTime)
    
    # Relaciones
    repositories = db.relationship('Repository', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    security_logs = db.relationship('SecurityLog', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Repository(db.Model):
    __tablename__ = 'repositories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    storage_type = db.Column(db.String(20), nullable=False)
    schedule = db.Column(db.String(20), default='manual')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_backup = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    
    # Relaciones
    backups = db.relationship('Backup', backref='repository', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'storage_type': self.storage_type,
            'schedule': self.schedule,
            'created_at': self.created_at.isoformat(),
            'last_backup': self.last_backup.isoformat() if self.last_backup else None,
            'status': self.status
        }

class Backup(db.Model):
    __tablename__ = 'backups'
    
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.Integer, db.ForeignKey('repositories.id'), nullable=False)
    local_path = db.Column(db.String(255))
    storage_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    repo_info = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    size = db.Column(db.BigInteger)
    
    def to_dict(self):
        return {
            'id': self.id,
            'repository_id': self.repository_id,
            'status': self.status,
            'error_message': self.error_message,
            'repo_info': json.loads(self.repo_info) if self.repo_info else None,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'size': self.size
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    duration = db.Column(db.Integer, default=5000)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'read': self.read,
            'duration': self.duration,
            'created_at': self.created_at.isoformat()
        }

class SecurityLog(db.Model):
    __tablename__ = 'security_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(80))
    action = db.Column(db.String(50), nullable=False)
    success = db.Column(db.Boolean, default=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'success': self.success,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat()
        } 