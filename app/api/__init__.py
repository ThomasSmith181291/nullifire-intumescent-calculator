from flask import Blueprint, jsonify

from app.db import get_ref_db

api_bp = Blueprint('api', __name__)


@api_bp.route('/health')
def health():
    try:
        db = get_ref_db()
        count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        return jsonify({'status': 'ok', 'db': 'connected', 'products': count})
    except Exception as e:
        return jsonify({'status': 'error', 'db': str(e)}), 500


# Import route modules so decorators register on api_bp
from app.api import sections  # noqa: F401, E402
from app.api import products  # noqa: F401, E402
from app.api import dft  # noqa: F401, E402
from app.api import projects  # noqa: F401, E402
from app.api import summary  # noqa: F401, E402
from app.api import import_export  # noqa: F401, E402
from app.api import grid  # noqa: F401, E402
from app.api import multi_product  # noqa: F401, E402
