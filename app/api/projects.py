from flask import request, jsonify

from app.api import api_bp
from app.services import project_service


@api_bp.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    required = ['name', 'product_id', 'fire_rating_id', 'failure_temp_id']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    project = project_service.create_project(
        name=data['name'],
        product_id=data['product_id'],
        fire_rating_id=data['fire_rating_id'],
        failure_temp_id=data['failure_temp_id'],
        client=data.get('client', ''),
        reference=data.get('reference', ''),
        origin_id=data.get('origin_id', 1),
    )
    return jsonify(project), 201


@api_bp.route('/projects')
def list_projects():
    return jsonify(project_service.list_projects())


@api_bp.route('/projects/<project_id>')
def get_project(project_id):
    project = project_service.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(project)


@api_bp.route('/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    project = project_service.update_project(project_id, **data)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(project)


@api_bp.route('/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    import os
    from flask import current_app
    db_dir = current_app.config['PROJECT_DB_DIR']
    db_path = os.path.join(db_dir, f'{project_id}.nfc')
    if os.path.exists(db_path):
        os.remove(db_path)
    return '', 204


@api_bp.route('/projects/<project_id>/members', methods=['POST'])
def add_member(project_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    if 'section_id' not in data or 'hp_profile_name' not in data:
        return jsonify({'error': 'section_id and hp_profile_name are required'}), 400

    member = project_service.add_member(
        project_id=project_id,
        section_id=data['section_id'],
        hp_profile_name=data['hp_profile_name'],
        quantity=data.get('quantity', 1),
        length_m=data.get('length_m', 0),
        zone=data.get('zone', ''),
        level=data.get('level', ''),
        fire_rating_id=data.get('fire_rating_id'),
        failure_temp_id=data.get('failure_temp_id'),
        product_id=data.get('product_id'),
    )
    if not member:
        return jsonify({'error': 'Project or section not found'}), 404
    return jsonify(member), 201


@api_bp.route('/projects/<project_id>/members/<member_id>', methods=['PUT'])
def update_member(project_id, member_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    member = project_service.update_member(project_id, member_id, **data)
    if not member:
        return jsonify({'error': 'Project or member not found'}), 404
    return jsonify(member)


@api_bp.route('/projects/<project_id>/members/<member_id>', methods=['DELETE'])
def delete_member(project_id, member_id):
    project_service.delete_member(project_id, member_id)
    return '', 204


@api_bp.route('/projects/<project_id>/members/batch-delete', methods=['POST'])
def batch_delete_members(project_id):
    data = request.get_json(silent=True)
    if not data or 'ids' not in data:
        return jsonify({'error': 'JSON body with ids array required'}), 400
    project_service.delete_members_batch(project_id, data['ids'])
    return '', 204
