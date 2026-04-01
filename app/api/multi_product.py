from flask import request, jsonify

from app.api import api_bp
from app.services import multi_product_service


@api_bp.route('/dft/compare', methods=['POST'])
def compare_products():
    """Check all Nullifire products for a given member specification."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    required = ['section_id', 'hp_profile_name', 'fire_rating_id', 'failure_temp_id']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing: {", ".join(missing)}'}), 400

    result = multi_product_service.check_member_coverage(
        data['section_id'], data['hp_profile_name'],
        data['fire_rating_id'], data['failure_temp_id']
    )
    return jsonify(result)
