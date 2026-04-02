import io
from flask import request, jsonify, Response

from app.api import api_bp
from app.services import import_service, export_service, project_service, product_service, summary_service, section_service


@api_bp.route('/import/parse', methods=['POST'])
def parse_import():
    """Parse an uploaded CSV/Excel file and return headers + sample data."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    f = request.files['file']
    content = f.read()
    try:
        headers, rows = import_service.parse_upload(content, f.filename)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # Auto-suggest column mapping
    mapping = import_service.auto_map_columns(headers)

    return jsonify({
        'headers': headers,
        'sample_rows': rows[:5],
        'total_rows': len(rows),
        'suggested_mapping': mapping,
        'all_rows': rows,
    })


@api_bp.route('/import/validate', methods=['POST'])
def validate_import():
    """Validate parsed rows against a column mapping using fuzzy matching."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    rows = data.get('rows', [])
    mapping = data.get('mapping', {})
    origin_id = data.get('origin_id')
    mapping = {k: int(v) for k, v in mapping.items()}

    results = import_service.validate_import_rows(rows, mapping, origin_id)
    valid_count = sum(1 for r in results if r['valid'])
    warning_count = sum(1 for r in results if r.get('warnings'))

    return jsonify({
        'results': results,
        'valid_count': valid_count,
        'warning_count': warning_count,
        'total_count': len(results),
    })


@api_bp.route('/projects/<project_id>/import', methods=['POST'])
def import_members(project_id):
    """Import validated rows as project members."""
    data = request.get_json(silent=True)
    if not data or 'members' not in data:
        return jsonify({'error': 'JSON body with members array required'}), 400

    project = project_service.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    added = []
    errors = []
    for i, m in enumerate(data['members']):
        try:
            section_id = m.get('section_id')
            if not section_id:
                errors.append({'row': i, 'error': 'Missing section_id'})
                continue

            # Determine default profile
            profiles = section_service.get_section_profiles(section_id, project['product_id'])
            hp_profile = m.get('hp_profile_name')
            if not hp_profile and profiles:
                hp_profile = profiles[0]['name']  # Use first available profile
            if not hp_profile:
                errors.append({'row': i, 'error': 'No valid profile found'})
                continue

            member = project_service.add_member(
                project_id=project_id,
                section_id=section_id,
                hp_profile_name=hp_profile,
                quantity=m.get('quantity', 1),
                length_m=m.get('length_m', 0),
                zone=m.get('zone', ''),
                level=m.get('level', ''),
                fire_rating_id=m.get('fire_rating_id'),
                failure_temp_id=m.get('failure_temp_id'),
                member_type=m.get('member_type', 'beam'),
            )
            if member:
                added.append(member)
            else:
                errors.append({'row': i, 'error': 'Failed to add member'})
        except Exception as e:
            errors.append({'row': i, 'error': str(e)})

    return jsonify({
        'added_count': len(added),
        'error_count': len(errors),
        'errors': errors[:10],
    })


@api_bp.route('/projects/<project_id>/export/excel')
def export_excel(project_id):
    """Export project as Excel file."""
    project = project_service.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    product = product_service.get_product(project['product_id'])
    members = project.get('members', [])

    excel_bytes = export_service.export_excel(project, members, product)

    filename = f'{project["name"].replace(" ", "_")}_specification.xlsx'
    return Response(
        excel_bytes,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@api_bp.route('/projects/<project_id>/export/pdf')
def export_pdf(project_id):
    """Export project as printable HTML report (print to PDF from browser)."""
    project = project_service.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    product = product_service.get_product(project['product_id'])
    members = project.get('members', [])
    summary_data = summary_service.calculate_project_summary(members, product)

    html = export_service.export_pdf_html(project, members, product, summary_data)
    return Response(html, mimetype='text/html')
