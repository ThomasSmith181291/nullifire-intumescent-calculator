from app.db import get_ref_db


def search_sections(query, origin_id=None, limit=50):
    db = get_ref_db()
    limit = min(limit, 100)
    params = [f'%{query}%']
    sql = '''
        SELECT s.id, s.serial_size, s.depth, s.width, s.web_thickness,
               s.flange_thickness, s.weight, s.area,
               s.steel_type_id, st.name AS steel_type_name, st.abbrev AS steel_type_abbrev,
               s.origin_id
        FROM steel_sections s
        JOIN steel_types st ON s.steel_type_id = st.id
        WHERE s.serial_size LIKE ?
    '''
    if origin_id is not None:
        sql += ' AND s.origin_id = ?'
        params.append(origin_id)
    sql += ' ORDER BY s.steel_type_id, s.group_sort, s.weight DESC LIMIT ?'
    params.append(limit)
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_section(section_id):
    db = get_ref_db()
    row = db.execute('''
        SELECT s.*, st.name AS steel_type_name, st.abbrev AS steel_type_abbrev,
               o.code AS origin_code
        FROM steel_sections s
        JOIN steel_types st ON s.steel_type_id = st.id
        JOIN origins o ON s.origin_id = o.id
        WHERE s.id = ?
    ''', (section_id,)).fetchone()
    return dict(row) if row else None


def get_section_profiles(section_id, product_id=None):
    db = get_ref_db()
    section = get_section(section_id)
    if not section:
        return None

    steel_type_id = section['steel_type_id']

    sql = '''
        SELECT DISTINCT hp.name, hp.description, hp.abbreviation, hp.faces,
               hp.hp_over_a_band, hp.is_composite, hp.default_profile
        FROM hp_profiles hp
        WHERE hp.steel_type_id = ? AND hp.board_only = 0
    '''
    params = [steel_type_id]

    if product_id is not None:
        sql += '''
            AND hp.name IN (
                SELECT c.hp_name FROM catalogue c
                JOIN products p ON c.band = p.catalogue_band
                WHERE p.id = ?
            )
        '''
        params.append(product_id)

    rows = db.execute(sql, params).fetchall()

    # Filter to profiles that have section factor data for this section
    result = []
    for row in rows:
        sf = db.execute('''
            SELECT hp_over_a FROM section_factors
            WHERE steel_section_id = ? AND hp_over_a_band = ?
        ''', (section_id, row['hp_over_a_band'])).fetchone()
        if sf:
            result.append(dict(row))

    return result


def get_section_factor(section_id, hp_profile_name):
    db = get_ref_db()
    profile = db.execute(
        'SELECT hp_over_a_band FROM hp_profiles WHERE name = ?',
        (hp_profile_name,)
    ).fetchone()
    if not profile:
        return None

    row = db.execute('''
        SELECT hp_over_a, heated_perimeter, hp_over_a_band
        FROM section_factors
        WHERE steel_section_id = ? AND hp_over_a_band = ?
    ''', (section_id, profile['hp_over_a_band'])).fetchone()
    return dict(row) if row else None
