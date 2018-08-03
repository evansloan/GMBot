import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = 'a;lsdkjfa;lsdkfj'
    DEBUG = False
    WTF_CSRF_ENABLED = True
    DEBUG_TB_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GROUPME_TOKEN = os.getenv('GROUPME_TOKEN')
    BASE_URL = os.getenv('BASE_URL')


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
    DEBUG_TB_ENABLED = True


class ProductionConfig(BaseConfig):
    SECRET_KEY = 'qGjitKhUIryObA32ff3fa34q1nTNLXCNtoE5'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    DEBUG_TB_ENABLED = False
