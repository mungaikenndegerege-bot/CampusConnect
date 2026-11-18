from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully.')
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
