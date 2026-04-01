from flask import Flask
from flask_cors import CORS

from app.config import DevelopmentConfig
from app.db import init_db


def create_app(config_class=None):
    if config_class is None:
        config_class = DevelopmentConfig

    app = Flask(
        __name__,
        static_folder=config_class.STATIC_FOLDER,
        static_url_path='/static'
    )
    app.config.from_object(config_class)

    init_db(app)
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    from app.api import api_bp
    from app.api.main import main_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)

    return app
