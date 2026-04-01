from app.db import get_ref_db


def get_products():
    db = get_ref_db()
    rows = db.execute('''
        SELECT id, name, density, solid_factor, offset_dft, catalogue_band,
               container_1_litres, container_2_litres, container_3_litres, container_4_litres,
               container_1_kg, container_2_kg, container_3_kg, container_4_kg,
               is_solvent_based, description
        FROM products
        WHERE is_discontinued = 0
        ORDER BY name
    ''').fetchall()
    return [dict(r) for r in rows]


def get_product(product_id):
    db = get_ref_db()
    row = db.execute('''
        SELECT id, name, density, solid_factor, offset_dft, catalogue_band,
               container_1_litres, container_2_litres, container_3_litres, container_4_litres,
               container_1_kg, container_2_kg, container_3_kg, container_4_kg,
               is_solvent_based, description
        FROM products
        WHERE id = ? AND is_discontinued = 0
    ''', (product_id,)).fetchone()
    return dict(row) if row else None


def get_product_fire_ratings(product_id):
    db = get_ref_db()
    rows = db.execute('''
        SELECT DISTINCT fr.id, fr.description, fr.abbrev, fr.short_abbrev
        FROM fire_ratings fr
        JOIN dft_data d ON d.fire_rating_id = fr.id
        WHERE d.product_id = ?
        ORDER BY fr.id
    ''', (product_id,)).fetchall()
    return [dict(r) for r in rows]


def get_product_failure_temps(product_id, fire_rating_id):
    db = get_ref_db()
    rows = db.execute('''
        SELECT DISTINCT ft.id, ft.description, ft.temp_id, ft.master_ft_id
        FROM failure_temps ft
        JOIN dft_data d ON d.failure_temp_id = ft.id
        WHERE d.product_id = ? AND d.fire_rating_id = ?
          AND ft.is_country_specific = 1
        ORDER BY ft.id
    ''', (product_id, fire_rating_id)).fetchall()
    return [dict(r) for r in rows]


def get_origins():
    db = get_ref_db()
    rows = db.execute('SELECT id, code, description FROM origins ORDER BY id').fetchall()
    return [dict(r) for r in rows]
