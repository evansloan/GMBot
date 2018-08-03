# gmbot.__init__.py

import configparser
import logging
import os
import re
from datetime import datetime

from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from groupy.client import Client
from jinja2 import evalcontextfilter, Markup
from rq import Queue
from ruamel.yaml import YAML

from src.worker import conn

app = Flask(
    __name__,
    template_folder='./web/templates',
    static_folder='./web/static'
)

app_settings = os.getenv('APP_SETTINGS', 'src.config.DevelopmentConfig')
app.config.from_object(app_settings)

del app.logger.handlers[:]
app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.formatter = logging.Formatter(
    fmt='[%(asctime)s] [%(levelname)s] %(module)s.py - line %(lineno)d: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
app.logger.addHandler(handler)

q = Queue(connection=conn)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)

groupme_token = app.config['GROUPME_TOKEN']
groupy_client = Client.from_token(groupme_token)

bots = []


class StringManager:
    def __init__(self, yaml_file):
        self.raw = yaml_file

        for k, v in self.raw.items():
            string_resource = StringResource(v)
            setattr(self, k, string_resource)


class StringResource:
    def __init__(self, strings):
        for k, v in strings.items():
            setattr(self, k, v)


yaml = YAML()
strings = StringManager(yaml.load(open('resources/strings.yml', 'r')))


from src.bot import GroupMeBot
from src.views import main_blueprint
app.register_blueprint(main_blueprint)


@app.before_first_request
def load_bots():
    """
    Loads all bots from bots.ini into a list accessible to the rest of the
    application
    """
    config = configparser.ConfigParser(interpolation=None)
    config.read('bots.ini')

    for bot in groupy_client.bots.list():
        if bot.callback_url == app.config['BASE_URL'] + '/callback':
            bots.append(GroupMeBot(bot.bot_id))

    for bot in bots:
        app.logger.info(f'{bot.group.name} loaded...')
    return bots


@app.errorhandler(401)
def unauthorized_page(error):
    return render_template('errors/401.html'), 401


@app.errorhandler(403)
def forbidden_page(error):
    return render_template('errors/403.html'), 403


@app.errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error_page(error):
    return render_template('errors/500.html'), 500


@app.template_filter()
def timesince(dt, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """

    now = datetime.utcnow()
    diff = now - dt

    periods = (
        (diff.days, 'day', 'days'),
        (diff.seconds / 3600, 'hour', 'hours'),
        (diff.seconds / 60, 'minute', 'minutes'),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return '%d %s ago' % (period, singular if period == 1 else plural)
    return default


@app.template_filter()
@evalcontextfilter
def linebreaks(eval_ctx, value):
    """Converts newlines into <p> and <br />s."""
    value = re.sub(r'\r\n|\r|\n', '\n', value)
    paras = re.split('\n{2,}', value)
    paras = [u'%s' % p.replace('\n', '<br />') for p in paras]
    paras = u'\n\n'.join(paras)
    return Markup(paras)
