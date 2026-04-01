from flask import request, jsonify

from app.api import api_bp
from app.services import dft_service

REQUIRED_FIELDS = ['section_id', 'hp_profile_name', 'product_id', 'fire_rating_id', 'failure_temp_id']


@api_bp.route('/dft/lookup', methods=['POST'])
def dft_lookup():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    result = dft_service.lookup_dft(
        section_id=data['section_id'],
        hp_profile_name=data['hp_profile_name'],
        product_id=data['product_id'],
        fire_rating_id=data['fire_rating_id'],
        failure_temp_id=data['failure_temp_id'],
    )
    return jsonify(result)
