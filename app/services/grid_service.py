"""Grid and level management for structural framing."""
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

    return {
        'gridlines': gridlines,
        'levels': levels,
        'members': [_row_to_dict(m) for m in members],
        'intersections': intersections,
    }
