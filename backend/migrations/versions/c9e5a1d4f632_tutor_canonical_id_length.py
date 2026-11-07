"""Match tutor canonical IDs to the 80-character canonical question IDs."""

from alembic import op
import sqlalchemy as sa

revision = 'c9e5a1d4f632'
down_revision = 'b8d4f0c3e521'
branch_labels = None
depends_on = None


def resize_canonical_id(previous, length):
    def alter():
        with op.batch_alter_table('tutor_materials') as batch:
            batch.alter_column(
                'canonical_id',
                existing_type=sa.String(previous),
                type_=sa.String(length),
                existing_nullable=True,
            )

    if op.get_bind().dialect.name != 'sqlite':
        alter()
        return

    # SQLite rebuilds this table, which existing help_events may reference.
    # PRAGMA foreign_keys must change outside a transaction to allow the rebuild.
    with op.get_context().autocommit_block():
        foreign_keys = op.get_bind().exec_driver_sql('PRAGMA foreign_keys').scalar()
        op.execute('PRAGMA foreign_keys=OFF')
        try:
            alter()
        finally:
            op.execute(f'PRAGMA foreign_keys={foreign_keys}')


def upgrade():
    resize_canonical_id(36, 80)


def downgrade():
    resize_canonical_id(80, 36)
