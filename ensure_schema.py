"""
Ensure all required columns exist in the SQLite database without breaking
existing data. Only adds columns that are missing.
"""
from app import create_app, db
from sqlalchemy import inspect, text

app = create_app()
with app.app_context():
    insp = inspect(db.engine)

    def add_col_if_missing(table, col, col_def):
        cols = [c['name'] for c in insp.get_columns(table)]
        if col not in cols:
            with db.engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}'))
                conn.commit()
            print(f'  Added {table}.{col}')
        else:
            print(f'  OK {table}.{col}')

    print('Checking post table...')
    add_col_if_missing('post', 'updated_at', 'DATETIME')
    add_col_if_missing('post', 'owner_token_hash', 'VARCHAR(64)')
    add_col_if_missing('post', 'file_path', 'VARCHAR(300)')
    add_col_if_missing('post', 'file_type', 'VARCHAR(20)')

    print('Checking marketplace_item table...')
    add_col_if_missing('marketplace_item', 'owner_token_hash', 'VARCHAR(64)')

    print('Checking lost_found_item table...')
    add_col_if_missing('lost_found_item', 'owner_token_hash', 'VARCHAR(64)')

    print('Checking announcement table...')
    add_col_if_missing('announcement', 'pinned', 'BOOLEAN DEFAULT 0')

    print('Checking ad table...')
    add_col_if_missing('ad', 'image_path', 'VARCHAR(255)')
    add_col_if_missing('ad', 'link_url', 'VARCHAR(500)')
    add_col_if_missing('ad', 'click_count', 'INTEGER DEFAULT 0')

    print('Checking comment table...')
    add_col_if_missing('comment', 'parent_id', 'INTEGER REFERENCES comment(id)')
    add_col_if_missing('comment', 'updated_at', 'DATETIME')

    print('Checking institution_post_comments table...')
    add_col_if_missing('institution_post_comments', 'poster_name', 'VARCHAR(100)')

    print('Checking account table...')
    add_col_if_missing('account', 'bio', 'TEXT')
    add_col_if_missing('account', 'institution_id', 'INTEGER REFERENCES institutions(id)')

    print('Done.')
