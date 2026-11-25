from app import create_app, db
app = create_app()
with app.app_context():
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    existing = set(insp.get_table_names())
    print('Missing tables check...')

    with db.engine.connect() as conn:
        if 'events' not in existing:
            conn.execute(text(
                "CREATE TABLE events ("
                "id INTEGER PRIMARY KEY, "
                "title VARCHAR(200) NOT NULL, "
                "description TEXT NOT NULL, "
                "institution_id INTEGER REFERENCES institutions(id), "
                "venue VARCHAR(200) NOT NULL, "
                "starts_at DATETIME NOT NULL, "
                "ends_at DATETIME, "
                "poster_name VARCHAR(100) NOT NULL, "
                "contact VARCHAR(100), "
                "poster_path VARCHAR(300), "
                "active BOOLEAN NOT NULL DEFAULT 1, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "owner_token_hash VARCHAR(64)"
                ")"
            ))
            conn.execute(text('CREATE INDEX ix_event_active_starts ON events (active, starts_at)'))
            conn.execute(text('CREATE INDEX ix_events_institution_id ON events (institution_id)'))
            conn.execute(text('CREATE INDEX ix_events_created_at ON events (created_at)'))
            conn.execute(text('CREATE INDEX ix_events_owner_token_hash ON events (owner_token_hash)'))
            print('Created events')

        if 'opportunities' not in existing:
            conn.execute(text(
                "CREATE TABLE opportunities ("
                "id INTEGER PRIMARY KEY, "
                "opportunity_type VARCHAR(20) NOT NULL, "
                "title VARCHAR(200) NOT NULL, "
                "organization VARCHAR(200) NOT NULL, "
                "description TEXT NOT NULL, "
                "location VARCHAR(200), "
                "application_url VARCHAR(500), "
                "institution_id INTEGER REFERENCES institutions(id), "
                "closes_at DATETIME, "
                "poster_name VARCHAR(100) NOT NULL, "
                "active BOOLEAN NOT NULL DEFAULT 1, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "owner_token_hash VARCHAR(64)"
                ")"
            ))
            conn.execute(text('CREATE INDEX ix_opportunity_active_created ON opportunities (active, created_at)'))
            conn.execute(text('CREATE INDEX ix_opportunities_opportunity_type ON opportunities (opportunity_type)'))
            conn.execute(text('CREATE INDEX ix_opportunities_institution_id ON opportunities (institution_id)'))
            conn.execute(text('CREATE INDEX ix_opportunities_closes_at ON opportunities (closes_at)'))
            conn.execute(text('CREATE INDEX ix_opportunities_owner_token_hash ON opportunities (owner_token_hash)'))
            print('Created opportunities')

        if 'reactions' not in existing:
            conn.execute(text(
                "CREATE TABLE reactions ("
                "id INTEGER PRIMARY KEY, "
                "account_id INTEGER NOT NULL REFERENCES account(id), "
                "target_type VARCHAR(30) NOT NULL, "
                "target_id INTEGER NOT NULL, "
                "reaction_type VARCHAR(20) NOT NULL DEFAULT 'like', "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(account_id, target_type, target_id)"
                ")"
            ))
            conn.execute(text('CREATE INDEX ix_reactions_account_id ON reactions (account_id)'))
            print('Created reactions')

        if 'notifications' not in existing:
            conn.execute(text(
                "CREATE TABLE notifications ("
                "id INTEGER PRIMARY KEY, "
                "account_id INTEGER NOT NULL REFERENCES account(id), "
                "title VARCHAR(200) NOT NULL, "
                "body VARCHAR(1000) NOT NULL, "
                "target_url VARCHAR(500), "
                "read_at DATETIME, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            ))
            conn.execute(text('CREATE INDEX ix_notifications_account_id ON notifications (account_id)'))
            conn.execute(text('CREATE INDEX ix_notifications_created_at ON notifications (created_at)'))
            print('Created notifications')

        if 'idempotency_records' not in existing:
            conn.execute(text(
                "CREATE TABLE idempotency_records ("
                "id INTEGER PRIMARY KEY, "
                "resource_type VARCHAR(40) NOT NULL, "
                "key_hash VARCHAR(64) NOT NULL, "
                "resource_id INTEGER NOT NULL, "
                "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                "UNIQUE(resource_type, key_hash)"
                ")"
            ))
            conn.execute(text('CREATE INDEX ix_idempotency_resource ON idempotency_records (resource_type, resource_id)'))
            conn.execute(text('CREATE INDEX ix_idempotency_records_created_at ON idempotency_records (created_at)'))
            print('Created idempotency_records')

        conn.commit()

    print('All tables ready.')
