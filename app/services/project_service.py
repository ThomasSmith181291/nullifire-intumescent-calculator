import os
import uuid
from datetime import datetime, timezone

from flask import current_app

from app.db import init_project_db, get_project_db
from app.services import section_service, product_service, dft_service, calc_service


def _now():
    return datetime.now(timezone.utc).isoformat()


def _member_to_dict(row):
    return {k: row[k] for k in row.keys()}


def _project_to_dict(row):
    return {k: row[k] for k in row.keys()}


def create_project(name, product_id, fire_rating_id, failure_temp_id,
                   client='', reference='', origin_id=1):
    project_id = str(uuid.uuid4())[:8]
    db_dir = current_app.config['PROJECT_DB_DIR']
    db_path = os.path.join(db_dir, f'{project_id}.nfc')

    db = init_project_db(db_path)
    now = _now()
    db.execute('''
        INSERT INTO projects (id, name, client, reference, product_id,
                              fire_rating_id, failure_temp_id, origin_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (project_id, name, client, reference, product_id,
          fire_rating_id, failure_temp_id, origin_id, now, now))
    db.commit()
    db.close()

    return get_project(project_id)


def get_project(project_id):
    db = get_project_db(project_id)
    if not db:
        return None
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return None
    result = _project_to_dict(project)
    members = db.execute('SELECT * FROM project_members ORDER BY sort_order, created_at').fetchall()
    result['members'] = [_member_to_dict(m) for m in members]
    return result


def update_project(project_id, **kwargs):
    db = get_project_db(project_id)
    if not db:
        return None

    allowed = {'name', 'client', 'reference', 'product_id', 'fire_rating_id',
               'failure_temp_id', 'origin_id'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_project(project_id)

    recalc_fields = {'product_id', 'fire_rating_id', 'failure_temp_id'}
    needs_recalc = any(k in recalc_fields for k in updates)

    updates['updated_at'] = _now()
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [project_id]
    db.execute(f'UPDATE projects SET {set_clause} WHERE id = ?', values)
    db.commit()

    if needs_recalc:
        _recalculate_default_members(project_id)

    return get_project(project_id)


def list_projects():
    db_dir = current_app.config['PROJECT_DB_DIR']
    projects = []
    if not os.path.exists(db_dir):
        return projects
    for fname in os.listdir(db_dir):
        if not fname.endswith('.nfc'):
            continue
        project_id = fname[:-4]
        try:
            db = get_project_db(project_id)
            if db:
                row = db.execute('SELECT id, name, client, updated_at FROM projects').fetchone()
                if row:
                    projects.append(_project_to_dict(row))
        except Exception:
            continue
    return sorted(projects, key=lambda p: p.get('updated_at', ''), reverse=True)


def add_member(project_id, section_id, hp_profile_name, quantity=1, length_m=0.0,
               zone='', level='', fire_rating_id=None, failure_temp_id=None, product_id=None):
    db = get_project_db(project_id)
    if not db:
        return None

    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return None

    section = section_service.get_section(section_id)
    if not section:
        return None

    member_id = str(uuid.uuid4())[:8]
    computed = _compute_member(project, section_id, hp_profile_name,
                               fire_rating_id, failure_temp_id, product_id,
                               quantity, length_m)

    db.execute('''
        INSERT INTO project_members
        (id, section_id, section_name, steel_type, hp_profile_name,
         hp_over_a, heated_perimeter, dft_mm, final_dft_mm,
         quantity, length_m, surface_area_m2, volume_litres, weight_kg,
         zone, level, fire_rating_id, failure_temp_id, product_id,
         status, sort_order, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (member_id, section_id, section['serial_size'],
          section.get('steel_type_abbrev', ''), hp_profile_name,
          computed['hp_over_a'], computed['heated_perimeter'],
          computed['dft_mm'], computed['final_dft_mm'],
          quantity, length_m,
          computed['surface_area_m2'], computed['volume_litres'], computed['weight_kg'],
          zone, level, fire_rating_id, failure_temp_id, product_id,
          computed['status'], 0, _now()))
    db.commit()

    return _member_to_dict(db.execute('SELECT * FROM project_members WHERE id = ?', (member_id,)).fetchone())


def update_member(project_id, member_id, **kwargs):
    db = get_project_db(project_id)
    if not db:
        return None

    member = db.execute('SELECT * FROM project_members WHERE id = ?', (member_id,)).fetchone()
    if not member:
        return None

    allowed = {'section_id', 'hp_profile_name', 'quantity', 'length_m', 'zone', 'level',
               'fire_rating_id', 'failure_temp_id', 'product_id', 'sort_order'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return _member_to_dict(member)

    recalc_triggers = {'section_id', 'hp_profile_name', 'quantity', 'length_m',
                       'fire_rating_id', 'failure_temp_id', 'product_id'}
    needs_recalc = any(k in recalc_triggers for k in updates)

    # Apply updates
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [member_id]
    db.execute(f'UPDATE project_members SET {set_clause} WHERE id = ?', values)
    db.commit()

    if needs_recalc:
        member = db.execute('SELECT * FROM project_members WHERE id = ?', (member_id,)).fetchone()
        project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()

        # Update section_name if section changed
        if 'section_id' in updates:
            section = section_service.get_section(member['section_id'])
            if section:
                db.execute('UPDATE project_members SET section_name=?, steel_type=? WHERE id=?',
                          (section['serial_size'], section.get('steel_type_abbrev', ''), member_id))

        computed = _compute_member(project, member['section_id'], member['hp_profile_name'],
                                   member['fire_rating_id'], member['failure_temp_id'],
                                   member['product_id'],
                                   member['quantity'], member['length_m'])
        db.execute('''
            UPDATE project_members SET
                hp_over_a=?, heated_perimeter=?, dft_mm=?, final_dft_mm=?,
                surface_area_m2=?, volume_litres=?, weight_kg=?, status=?
            WHERE id=?
        ''', (computed['hp_over_a'], computed['heated_perimeter'],
              computed['dft_mm'], computed['final_dft_mm'],
              computed['surface_area_m2'], computed['volume_litres'],
              computed['weight_kg'], computed['status'], member_id))
        db.commit()

    return _member_to_dict(db.execute('SELECT * FROM project_members WHERE id = ?', (member_id,)).fetchone())


def delete_member(project_id, member_id):
    db = get_project_db(project_id)
    if not db:
        return False
    db.execute('DELETE FROM project_members WHERE id = ?', (member_id,))
    db.commit()
    return True


def delete_members_batch(project_id, member_ids):
    db = get_project_db(project_id)
    if not db:
        return False
    placeholders = ','.join('?' for _ in member_ids)
    db.execute(f'DELETE FROM project_members WHERE id IN ({placeholders})', member_ids)
    db.commit()
    return True


def _compute_member(project, section_id, hp_profile_name,
                    member_fr_id, member_ft_id, member_product_id,
                    quantity, length_m):
    eff_product_id = member_product_id or project['product_id']
    eff_fr_id = member_fr_id or project['fire_rating_id']
    eff_ft_id = member_ft_id or project['failure_temp_id']

    dft_result = dft_service.lookup_dft(section_id, hp_profile_name,
                                         eff_product_id, eff_fr_id, eff_ft_id)

    product = product_service.get_product(eff_product_id)
    # solid_factor is stored as percentage (e.g., 85 = 85%), convert to decimal
    sf_raw = product['solid_factor'] if product and product['solid_factor'] else 100
    solid_factor = sf_raw / 100.0 if sf_raw > 1 else sf_raw
    # density is in kg/m3, convert to kg/litre
    density = product['density'] if product and product['density'] else 1000
    density_kg_per_litre = density / 1000.0

    hp_mm = (dft_result['heated_perimeter'] or 0) * 1000  # convert m to mm

    quantities = calc_service.calculate_member_quantities(
        dft_mm=dft_result.get('final_dft_mm') or dft_result.get('dft_mm'),
        heated_perimeter_mm=hp_mm,
        length_m=length_m or 0,
        quantity=quantity or 1,
        solid_factor=solid_factor,
        density=density_kg_per_litre,
    )

    return {
        'hp_over_a': dft_result.get('hp_over_a'),
        'heated_perimeter': dft_result.get('heated_perimeter'),
        'dft_mm': dft_result.get('dft_mm'),
        'final_dft_mm': dft_result.get('final_dft_mm'),
        'surface_area_m2': quantities['surface_area_m2'],
        'volume_litres': quantities['volume_litres'],
        'weight_kg': quantities['weight_kg'],
        'status': dft_result.get('status', 'error'),
    }


def _recalculate_default_members(project_id):
    db = get_project_db(project_id)
    if not db:
        return
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    members = db.execute('''
        SELECT * FROM project_members
        WHERE fire_rating_id IS NULL OR failure_temp_id IS NULL OR product_id IS NULL
    ''').fetchall()

    for member in members:
        computed = _compute_member(project, member['section_id'], member['hp_profile_name'],
                                   member['fire_rating_id'], member['failure_temp_id'],
                                   member['product_id'],
                                   member['quantity'], member['length_m'])
        db.execute('''
            UPDATE project_members SET
                hp_over_a=?, heated_perimeter=?, dft_mm=?, final_dft_mm=?,
                surface_area_m2=?, volume_litres=?, weight_kg=?, status=?
            WHERE id=?
        ''', (computed['hp_over_a'], computed['heated_perimeter'],
              computed['dft_mm'], computed['final_dft_mm'],
              computed['surface_area_m2'], computed['volume_litres'],
              computed['weight_kg'], computed['status'], member['id']))
    db.commit()
