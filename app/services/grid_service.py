"""Grid and level management for structural framing."""
import math
import uuid
from app.db import get_project_db


def _row_to_dict(row):
    return {k: row[k] for k in row.keys()} if row else None


def get_gridlines(project_id):
    db = get_project_db(project_id)
    if not db:
        return []
    rows = db.execute('SELECT * FROM gridlines ORDER BY direction, sort_order').fetchall()
    return [_row_to_dict(r) for r in rows]


def add_gridline(project_id, direction, name, position, sort_order=0):
    db = get_project_db(project_id)
    if not db:
        return None
    gid = str(uuid.uuid4())[:8]
    db.execute('INSERT INTO gridlines (id, direction, name, position, sort_order) VALUES (?,?,?,?,?)',
               (gid, direction, name, position, sort_order))
    db.commit()
    return _row_to_dict(db.execute('SELECT * FROM gridlines WHERE id=?', (gid,)).fetchone())


def update_gridline(project_id, gridline_id, **kwargs):
    db = get_project_db(project_id)
    if not db:
        return None
    allowed = {'name', 'position', 'sort_order'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if updates:
        set_clause = ', '.join(f'{k}=?' for k in updates)
        db.execute(f'UPDATE gridlines SET {set_clause} WHERE id=?', list(updates.values()) + [gridline_id])
        db.commit()
    return _row_to_dict(db.execute('SELECT * FROM gridlines WHERE id=?', (gridline_id,)).fetchone())


def delete_gridline(project_id, gridline_id):
    db = get_project_db(project_id)
    if not db:
        return False
    db.execute('DELETE FROM gridlines WHERE id=?', (gridline_id,))
    db.commit()
    return True


def get_levels(project_id):
    db = get_project_db(project_id)
    if not db:
        return []
    rows = db.execute('SELECT * FROM levels ORDER BY height').fetchall()
    return [_row_to_dict(r) for r in rows]


def add_level(project_id, name, height, fire_rating_id=None, failure_temp_id=None, sort_order=0):
    db = get_project_db(project_id)
    if not db:
        return None
    lid = str(uuid.uuid4())[:8]
    db.execute('''INSERT INTO levels (id, name, height, fire_rating_id, failure_temp_id, sort_order)
                  VALUES (?,?,?,?,?,?)''',
               (lid, name, height, fire_rating_id, failure_temp_id, sort_order))
    db.commit()
    return _row_to_dict(db.execute('SELECT * FROM levels WHERE id=?', (lid,)).fetchone())


def update_level(project_id, level_id, **kwargs):
    db = get_project_db(project_id)
    if not db:
        return None
    allowed = {'name', 'height', 'fire_rating_id', 'failure_temp_id', 'sort_order'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if updates:
        set_clause = ', '.join(f'{k}=?' for k in updates)
        db.execute(f'UPDATE levels SET {set_clause} WHERE id=?', list(updates.values()) + [level_id])
        db.commit()
    return _row_to_dict(db.execute('SELECT * FROM levels WHERE id=?', (level_id,)).fetchone())


def delete_level(project_id, level_id):
    db = get_project_db(project_id)
    if not db:
        return False
    db.execute('DELETE FROM levels WHERE id=?', (level_id,))
    db.commit()
    return True


def get_3d_scene_data(project_id):
    """Get all data needed to render the 3D scene."""
    db = get_project_db(project_id)
    if not db:
        return None

    gridlines = get_gridlines(project_id)
    levels = get_levels(project_id)
    members = db.execute('SELECT * FROM project_members ORDER BY sort_order').fetchall()

    # Build grid intersection lookup
    x_lines = [g for g in gridlines if g['direction'] == 'x']
    y_lines = [g for g in gridlines if g['direction'] == 'y']

    intersections = {}
    for x in x_lines:
        for y in y_lines:
            key = f"{x['name']}/{y['name']}"
            intersections[key] = {'x': x['position'], 'y': y['position']}

    level_map = {l['name']: l['height'] for l in levels}

    return {
        'gridlines': gridlines,
        'levels': levels,
        'members': [_row_to_dict(m) for m in members],
        'intersections': intersections,
        'level_map': level_map,
    }


def batch_add_gridlines(project_id, gridlines_data):
    """Add multiple gridlines at once. Each item: {direction, name, position}."""
    db = get_project_db(project_id)
    if not db:
        return []
    results = []
    for i, gl in enumerate(gridlines_data):
        gid = str(uuid.uuid4())[:8]
        db.execute('INSERT INTO gridlines (id, direction, name, position, sort_order) VALUES (?,?,?,?,?)',
                   (gid, gl['direction'], gl['name'], gl['position'], i))
        results.append({'id': gid, **gl, 'sort_order': i})
    db.commit()
    return results


def batch_add_levels(project_id, levels_data):
    """Add multiple levels at once. Each item: {name, height}."""
    db = get_project_db(project_id)
    if not db:
        return []
    results = []
    for i, lv in enumerate(levels_data):
        lid = str(uuid.uuid4())[:8]
        db.execute('INSERT INTO levels (id, name, height, fire_rating_id, failure_temp_id, sort_order) VALUES (?,?,?,?,?,?)',
                   (lid, lv['name'], lv['height'], lv.get('fire_rating_id'), lv.get('failure_temp_id'), i))
        results.append({'id': lid, **lv, 'sort_order': i})
    db.commit()
    return results


def clear_gridlines(project_id):
    """Remove all gridlines from a project."""
    db = get_project_db(project_id)
    if db:
        db.execute('DELETE FROM gridlines')
        db.commit()


def clear_levels(project_id):
    """Remove all levels from a project."""
    db = get_project_db(project_id)
    if db:
        db.execute('DELETE FROM levels')
        db.commit()


def calculate_member_length(project_id, grid_from, grid_to, level_from_name, level_to_name):
    """
    Calculate the 3D length between two grid positions at (potentially different) levels.
    Supports horizontal beams, vertical columns, and diagonal bracing/rafters.
    Returns length in metres.
    """
    gridlines = get_gridlines(project_id)
    levels = get_levels(project_id)

    x_map = {g['name']: g['position'] for g in gridlines if g['direction'] == 'x'}
    y_map = {g['name']: g['position'] for g in gridlines if g['direction'] == 'y'}
    level_map = {l['name']: l['height'] for l in levels}

    # Parse grid references (format: "A/1" or just "A" for columns)
    def parse_grid_ref(ref):
        if '/' in ref:
            parts = ref.split('/')
            return x_map.get(parts[0], 0), y_map.get(parts[1], 0)
        # Single reference — could be x or y
        if ref in x_map:
            return x_map[ref], 0
        if ref in y_map:
            return 0, y_map[ref]
        return 0, 0

    x1, y1 = parse_grid_ref(grid_from)
    x2, y2 = parse_grid_ref(grid_to)
    z1 = level_map.get(level_from_name, 0)
    z2 = level_map.get(level_to_name, 0)

    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1

    return round(math.sqrt(dx * dx + dy * dy + dz * dz), 3)
