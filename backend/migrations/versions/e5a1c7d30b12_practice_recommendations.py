"""Adaptive practice: session kind and the audit of each recommendation."""
from alembic import op
import sqlalchemy as sa

revision = 'e5a1c7d30b12'
down_revision = 'd410a4e02001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('diagnostic_sessions') as batch:
        batch.add_column(sa.Column('kind', sa.String(20), nullable=False, server_default='diagnostic'))
    op.create_table('recommendation_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('diagnostic_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.String(100), nullable=False),
        sa.Column('policy_version', sa.String(40), nullable=False),
        sa.Column('function', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(300), nullable=False),
        sa.Column('components', sa.JSON(), nullable=False),
        sa.Column('candidates_total', sa.Integer(), nullable=False),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.UniqueConstraint('session_id', 'position'))
    op.create_index('ix_recommendation_events_user_id', 'recommendation_events', ['user_id'])
    op.create_index('ix_recommendation_events_session_id', 'recommendation_events', ['session_id'])


def downgrade():
    op.drop_index('ix_recommendation_events_session_id', table_name='recommendation_events')
    op.drop_index('ix_recommendation_events_user_id', table_name='recommendation_events')
    op.drop_table('recommendation_events')
    op.execute("DELETE FROM learning_events WHERE session_id IN (SELECT id FROM diagnostic_sessions WHERE kind = 'practice')")
    op.execute("DELETE FROM diagnostic_sessions WHERE kind = 'practice'")
    with op.batch_alter_table('diagnostic_sessions') as batch:
        batch.drop_column('kind')
