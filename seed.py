from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully.')
    # Idempotent column additions for post and institution_posts tables
    import sqlalchemy as _sa
    _engine = db.engine
    _inspector = _sa.inspect(_engine)

    def _add_col_if_missing(table, col_name, col_def):
        cols = [c['name'] for c in _inspector.get_columns(table)]
        if col_name not in cols:
            with _engine.connect() as _conn:
                _conn.execute(_sa.text(f'ALTER TABLE {table} ADD COLUMN {col_def}'))
                _conn.commit()
            print(f'Added column {col_name} to {table}')

    _add_col_if_missing('post', 'file_path', 'file_path VARCHAR(300)')
    _add_col_if_missing('post', 'file_type', 'file_type VARCHAR(20)')
    _add_col_if_missing('institution_posts', 'file_path', 'file_path VARCHAR(300)')
    _add_col_if_missing('institution_posts', 'file_type', 'file_type VARCHAR(20)')
    from app.institutions_seed import seed_institutions
    seed_institutions()
    from app.models import AdPlacement
    _placements = [
        {'name': 'Feed Banner',           'description': 'Appears every 5 posts in the main feed',   'price_per_day': 500.0},
        {'name': 'Institution Community', 'description': 'Appears in institution community feeds',    'price_per_day': 300.0},
        {'name': 'Homepage Top',          'description': 'Top banner on homepage',                   'price_per_day': 800.0},
        {'name': 'Sidebar',               'description': 'Sidebar placement on desktop',             'price_per_day': 200.0},
    ]
    for _p in _placements:
        if not AdPlacement.query.filter_by(name=_p['name']).first():
            db.session.add(AdPlacement(**_p))
    db.session.commit()
    print('Ad placements seeded.')
