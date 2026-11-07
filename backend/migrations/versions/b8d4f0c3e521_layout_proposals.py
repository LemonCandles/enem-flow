"""Layout proposals converted by the versioned adapter and their review."""
from alembic import op
import sqlalchemy as sa

revision = 'b8d4f0c3e521'
down_revision = 'a7c3e9b2d410'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('layout_proposals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('question_version_id', sa.String(100), sa.ForeignKey('question_versions.id'), nullable=False),
        sa.Column('adapter_version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('proposal', sa.JSON(), nullable=False),
        sa.Column('converted', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=False),
        sa.Column('comparison', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.Float(), nullable=False),
        sa.Column('reviewed_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.Float(), nullable=True),
        sa.Column('review_reason', sa.String(2000), nullable=True),
        sa.Column('result_version_id', sa.String(100), nullable=True))
    op.create_index('ix_layout_proposals_question_version_id', 'layout_proposals', ['question_version_id'])


def downgrade():
    op.drop_index('ix_layout_proposals_question_version_id', table_name='layout_proposals')
    op.drop_table('layout_proposals')
