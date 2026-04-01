from flask import request, jsonify

from app.api import api_bp
from app.services import section_service


@api_bp.route('/sections/types')
def get_steel_types():
    return jsonify(section_service.get_steel_types())


@api_bp.route('/sections/types/<int:type_id>')
def get_sections_by_type(type_id):
    origin_id = request.args.get('origin', type=int)
    return jsonify(section_service.get_sections_by_type(type_id, origin_id))


@api_bp.route('/sections/search')
def search_sections():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'error': 'Query parameter q is required'}), 400
    origin_id = request.args.get('origin', type=int)
    limit = request.args.get('limit', 50, type=int)
    results = section_service.search_sections(q, origin_id=origin_id, limit=limit)
    return jsonify(results)


@api_bp.route('/sections/<int:section_id>')
def get_section(section_id):
    section = section_service.get_section(section_id)
    if not section:
        return jsonify({'error': 'Section not found'}), 404
    return jsonify(section)


@api_bp.route('/sections/<int:section_id>/profiles')
def get_section_profiles(section_id):
    product_id = request.args.get('product_id', type=int)
    profiles = section_service.get_section_profiles(section_id, product_id=product_id)
    if profiles is None:
        return jsonify({'error': 'Section not found'}), 404
    return jsonify(profiles)


@api_bp.route('/sections/<int:section_id>/factor')
def get_section_factor(section_id):
    profile = request.args.get('profile', '').strip()
    if not profile:
        return jsonify({'error': 'Query parameter profile is required'}), 400
    factor = section_service.get_section_factor(section_id, profile)
    if not factor:
        return jsonify({'error': 'No section factor found for this section/profile combination'}), 404
    return jsonify(factor)
