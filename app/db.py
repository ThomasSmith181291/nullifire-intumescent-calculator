import os
import sqlite3

from flask import g, current_app


def get_ref_db():
    if 'ref_db' not in g:
        db_path = current_app.config['REF_DB_PATH']
        g.ref_db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        g.ref_db.row_factory = sqlite3.Row
    return g.ref_db


def close_ref_db(e=None):
    db = g.pop('ref_db', None)
    if db is not None:
        db.close()


PROJECT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    client TEXT DEFAULT '',
    reference TEXT DEFAULT '',
    product_id INTEGER NOT NULL,
    fire_rating_id INTEGER NOT NULL,
    failure_temp_id INTEGER NOT NULL,
    origin_id INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_members (
    id TEXT PRIMARY KEY,
    section_id INTEGER NOT NULL,
    section_name TEXT,
    steel_type TEXT,
    hp_profile_name TEXT NOT NULL,
    hp_over_a REAL,
    heated_perimeter REAL,
    dft_mm REAL,
    final_dft_mm REAL,
    quantity INTEGER DEFAULT 1,
    length_m REAL DEFAULT 0,
    surface_area_m2 REAL DEFAULT 0,
    volume_litres REAL DEFAULT 0,
    weight_kg REAL DEFAULT 0,
    zone TEXT DEFAULT '',
    level TEXT DEFAULT '',
    fire_rating_id INTEGER,
    failure_temp_id INTEGER,
    product_id INTEGER,
    status TEXT DEFAULT 'pending',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
'''


def init_project_db(db_path):
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript(PROJECT_SCHEMA)
    return db


def get_project_db(project_id):
    key = f'project_db_{project_id}'
    db = getattr(g, key, None)
    if db is None:
        db_dir = current_app.config['PROJECT_DB_DIR']
        db_path = os.path.join(db_dir, f'{project_id}.nfc')
        if not os.path.exists(db_path):
            return None
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        setattr(g, key, db)
    return db


def close_all_dbs(e=None):
    for key in list(vars(g)):
        if key.startswith('project_db_'):
            db = g.pop(key, None)
            if db:
                db.close()
    db = g.pop('ref_db', None)
    if db:
        db.close()


def init_db(app):
    db_path = app.config['REF_DB_PATH']
    if not os.path.exists(db_path):
        raise FileNotFoundError(f'Reference database not found: {db_path}')
    os.makedirs(app.config.get('PROJECT_DB_DIR', 'data/projects'), exist_ok=True)
    app.teardown_appcontext(close_all_dbs)
