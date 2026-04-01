from flask import request, jsonify

from app.api import api_bp
from app.services import project_service, product_service, summary_service, verification_service


@api_bp.route('/projects/<project_id>/summary')
def get_project_summary(project_id):
    project = project_service.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    product = product_service.get_product(project['product_id'])
    members = project.get('members', [])

    totals = summary_service.calculate_project_summary(members, product)
    verification = verification_service.get_verification_summary(members)
    zone_subtotals = summary_service.calculate_subtotals(members, 'zone')
    level_subtotals = summary_service.calculate_subtotals(members, 'level')

    return jsonify({
        **totals,
        'verification': verification,
        'zone_subtotals': zone_subtotals,
        'level_subtotals': level_subtotals,
    })
