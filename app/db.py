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


def init_db(app):
    db_path = app.config['REF_DB_PATH']
    if not os.path.exists(db_path):
        raise FileNotFoundError(f'Reference database not found: {db_path}')
    app.teardown_appcontext(close_ref_db)
