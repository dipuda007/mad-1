import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'placement-portal-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'placement_portal.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
