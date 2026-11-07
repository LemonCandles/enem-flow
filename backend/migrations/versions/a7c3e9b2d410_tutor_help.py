"""Tutor: approved help material and the help events of practice sessions."""
from alembic import op
import sqlalchemy as sa

revision = 'a7c3e9b2d410'
down_revision = 'e5a1c7d30b12'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('tutor_materials',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('question_id', sa.String(100), nullable=False),
        sa.Column('canonical_id', sa.String(36), nullable=True),
        sa.Column('content_sha256', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('origin', sa.String(20), nullable=False),
        sa.Column('levels', sa.JSON(), nullable=False),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('reviewed_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.Float(), nullable=True),
        sa.Column('review_reason', sa.String(2000), nullable=True),
        sa.UniqueConstraint('question_id', 'version'))
    op.create_index('ix_tutor_materials_question_id', 'tutor_materials', ['question_id'])
    op.create_index('ix_tutor_materials_canonical_id', 'tutor_materials', ['canonical_id'])
    op.create_index('ix_tutor_materials_content_sha256', 'tutor_materials', ['content_sha256'])
    op.create_table('help_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('diagnostic_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.String(100), nullable=False),
        sa.Column('content_version', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('request_key', sa.String(80), nullable=False),
        sa.Column('material_id', sa.String(36), sa.ForeignKey('tutor_materials.id'), nullable=False),
        sa.Column('outcome', sa.String(20), nullable=False),
        sa.Column('mode', sa.String(20), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('provider', sa.JSON(), nullable=False),
        sa.Column('requested_at', sa.Float(), nullable=False),
        sa.Column('delivered_at', sa.Float(), nullable=True),
        sa.UniqueConstraint('user_id', 'request_key'))
    op.create_index('ix_help_events_user_id', 'help_events', ['user_id'])
    op.create_index('ix_help_events_session_id', 'help_events', ['session_id'])


def downgrade():
    op.drop_index('ix_help_events_session_id', table_name='help_events')
    op.drop_index('ix_help_events_user_id', table_name='help_events')
    op.drop_table('help_events')
    op.drop_index('ix_tutor_materials_content_sha256', table_name='tutor_materials')
    op.drop_index('ix_tutor_materials_canonical_id', table_name='tutor_materials')
    op.drop_index('ix_tutor_materials_question_id', table_name='tutor_materials')
    op.drop_table('tutor_materials')
