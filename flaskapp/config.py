import os
basedir = os.path.abspath(os.path.dirname(__file__))

db_url = os.environ.get("DATABASE_URL")


class Config(object):
    DEBUG = False
    TESTING = False
    CSRF_ENABLED = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key'

    SQLALCHEMY_DATABASE_URI = db_url


class ProductionConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = db_url.replace("postgres://", "postgresql://")


class StagingConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
