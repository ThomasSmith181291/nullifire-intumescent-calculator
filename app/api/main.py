from flask import Blueprint, send_from_directory, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return send_from_directory(current_app.config['STATIC_FOLDER'], 'index.html')
