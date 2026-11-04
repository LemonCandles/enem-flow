"""Diagnostic sessions and exclusive learning event origins."""
from alembic import op
import sqlalchemy as sa

revision = 'd410a4e02001'
down_revision = 'f831ef101a02'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('diagnostic_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_key', sa.String(80), nullable=False),
        sa.Column('objective', sa.String(120), nullable=False),
        sa.Column('area', sa.String(80), nullable=False),
        sa.Column('available_minutes', sa.Integer(), nullable=False),
        sa.Column('selection', sa.JSON(), nullable=False),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.Float(), nullable=False),
        sa.Column('finished_at', sa.Float(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.UniqueConstraint('user_id', 'start_key'))
    op.create_index('ix_diagnostic_sessions_user_id', 'diagnostic_sessions', ['user_id'])
    with op.batch_alter_table('learning_events') as batch:
        batch.alter_column('run_id', existing_type=sa.String(36), nullable=True)
        batch.add_column(sa.Column('session_id', sa.String(36), nullable=True))
        batch.create_foreign_key('fk_learning_events_session_id', 'diagnostic_sessions', ['session_id'], ['id'], ondelete='CASCADE')
        batch.create_index('ix_learning_events_session_id', ['session_id'])
        batch.create_unique_constraint('uq_learning_events_session_item', ['session_id', 'item_id'])
        batch.create_check_constraint('learning_event_origin', '(run_id IS NOT NULL AND session_id IS NULL) OR (run_id IS NULL AND session_id IS NOT NULL)')


def downgrade():
    op.execute('DELETE FROM learning_events WHERE session_id IS NOT NULL')
    with op.batch_alter_table('learning_events') as batch:
        batch.drop_constraint('learning_event_origin', type_='check')
        batch.drop_constraint('uq_learning_events_session_item', type_='unique')
        batch.drop_index('ix_learning_events_session_id')
        batch.drop_constraint('fk_learning_events_session_id', type_='foreignkey')
        batch.drop_column('session_id')
        batch.alter_column('run_id', existing_type=sa.String(36), nullable=False)
    op.drop_index('ix_diagnostic_sessions_user_id', table_name='diagnostic_sessions')
    op.drop_table('diagnostic_sessions')
