"""Create the existing platform schema and add the current platform tables.

Revision ID: 14b68d026ace
Revises:
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app import db


revision = '14b68d026ace'
down_revision = None
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name, column):
    existing = {item['name'] for item in inspect(op.get_bind()).get_columns(table_name)}
    if column.name not in existing:
        if op.get_bind().dialect.name == 'sqlite':
            with op.batch_alter_table(table_name) as batch:
                batch.add_column(column)
        else:
            op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())
    if not existing_tables:
        db.metadata.create_all(bind=bind)
        return

    if 'account' in existing_tables:
        _add_column_if_missing(
            'account',
            sa.Column('institution_id', sa.Integer(),
                      sa.ForeignKey(
                          'institutions.id',
                          name='fk_account_institution_id_institutions',
                      ),
                      nullable=True),
        )
    for table_name in ('post', 'marketplace_item', 'lost_found_item', 'institution_posts'):
        if table_name in existing_tables:
            _add_column_if_missing(
                table_name,
                sa.Column('owner_token_hash', sa.String(length=64), nullable=True),
            )

    db.metadata.create_all(bind=bind)
    for table in db.metadata.sorted_tables:
        if table.name in set(inspect(bind).get_table_names()):
            for index in table.indexes:
                index.create(bind=bind, checkfirst=True)


def downgrade():
    raise RuntimeError(
        'The initial platform migration is intentionally non-destructive. '
        'Restore from a verified backup instead of downgrading the baseline.'
    )
