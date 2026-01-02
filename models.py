from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, company, student
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    company = db.relationship('Company', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    branch = db.Column(db.String(50))
    cgpa = db.Column(db.Float, default=0.0)
    resume_url = db.Column(db.String(255))
    is_blacklisted = db.Column(db.Boolean, default=False)
    
    # Relationships
    applications = db.relationship('Application', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.name}>'


class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    hr_name = db.Column(db.String(100))
    hr_email = db.Column(db.String(120))
    hr_phone = db.Column(db.String(15))
    website = db.Column(db.String(255))
    description = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    is_blacklisted = db.Column(db.Boolean, default=False)
    
    # Relationships
    placement_drives = db.relationship('PlacementDrive', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Company {self.name}>'


class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    job_description = db.Column(db.Text)
    eligibility_criteria = db.Column(db.Text)
    min_cgpa = db.Column(db.Float, default=0.0)
    branches_allowed = db.Column(db.String(255))  # Comma-separated list
    package_lpa = db.Column(db.Float)
    application_deadline = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, approved, closed, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='drive', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PlacementDrive {self.job_title}>'


class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='applied')  # applied, shortlisted, selected, rejected
    
    # Unique constraint to prevent duplicate applications
    __table_args__ = (db.UniqueConstraint('student_id', 'drive_id', name='unique_student_drive'),)
    
    def __repr__(self):
        return f'<Application {self.id}>'
