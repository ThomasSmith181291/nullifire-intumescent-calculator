import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    REF_DB_PATH = os.path.join(BASE_DIR, 'data', 'nullifire.db')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    PROJECT_DB_DIR = os.path.join(BASE_DIR, 'data', 'projects')


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
