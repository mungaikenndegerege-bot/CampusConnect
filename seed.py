from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created successfully.')
    from app.institutions_seed import seed_institutions
    seed_institutions()
