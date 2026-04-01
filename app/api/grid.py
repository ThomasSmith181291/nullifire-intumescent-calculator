from flask import request, jsonify

from app.api import api_bp
from app.services import grid_service


@api_bp.route('/projects/<project_id>/gridlines')
def get_gridlines(project_id):
    return jsonify(grid_service.get_gridlines(project_id))


@api_bp.route('/projects/<project_id>/gridlines', methods=['POST'])
def add_gridline(project_id):
    data = request.get_json(silent=True)
    if not data or 'direction' not in data or 'name' not in data or 'position' not in data:
        return jsonify({'error': 'direction, name, and position are required'}), 400
    gl = grid_service.add_gridline(project_id, data['direction'], data['name'],
                                    data['position'], data.get('sort_order', 0))
    return jsonify(gl), 201


@api_bp.route('/projects/<project_id>/gridlines/<gridline_id>', methods=['PUT'])
def update_gridline(project_id, gridline_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    gl = grid_service.update_gridline(project_id, gridline_id, **data)
    return jsonify(gl)


@api_bp.route('/projects/<project_id>/gridlines/<gridline_id>', methods=['DELETE'])
def delete_gridline(project_id, gridline_id):
    grid_service.delete_gridline(project_id, gridline_id)
    return '', 204


@api_bp.route('/projects/<project_id>/levels')
def get_levels(project_id):
    return jsonify(grid_service.get_levels(project_id))


@api_bp.route('/projects/<project_id>/levels', methods=['POST'])
def add_level(project_id):
    data = request.get_json(silent=True)
    if not data or 'name' not in data or 'height' not in data:
        return jsonify({'error': 'name and height are required'}), 400
    level = grid_service.add_level(project_id, data['name'], data['height'],
                                    data.get('fire_rating_id'), data.get('failure_temp_id'),
                                    data.get('sort_order', 0))
    return jsonify(level), 201


@api_bp.route('/projects/<project_id>/levels/<level_id>', methods=['PUT'])
def update_level(project_id, level_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    level = grid_service.update_level(project_id, level_id, **data)
    return jsonify(level)


@api_bp.route('/projects/<project_id>/levels/<level_id>', methods=['DELETE'])
def delete_level(project_id, level_id):
    grid_service.delete_level(project_id, level_id)
    return '', 204


@api_bp.route('/projects/<project_id>/scene')
def get_scene_data(project_id):
    """Get complete 3D scene data (gridlines, levels, members, intersections)."""
    data = grid_service.get_3d_scene_data(project_id)
    if not data:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(data)
