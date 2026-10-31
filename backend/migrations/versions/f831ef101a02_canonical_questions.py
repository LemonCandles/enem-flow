"""Canonical identity separate from immutable occurrence versions.

Revision ID: f831ef101a02
Revises: ca6b8a81a1c9
"""
from alembic import op
import sqlalchemy as sa

revision='f831ef101a02'
down_revision='ca6b8a81a1c9'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('canonical_questions',sa.Column('id',sa.String(80),primary_key=True),
                    sa.Column('signature',sa.String(64),nullable=False,unique=True),
                    sa.Column('answer_signature',sa.String(64),nullable=True))
    with op.batch_alter_table('question_versions') as batch:
        batch.add_column(sa.Column('canonical_id',sa.String(80),nullable=True))
        batch.create_foreign_key('fk_question_versions_canonical_id','canonical_questions',['canonical_id'],['id'])
        batch.create_index('ix_question_versions_canonical_id',['canonical_id'])


def downgrade():
    with op.batch_alter_table('question_versions') as batch:
        batch.drop_index('ix_question_versions_canonical_id')
        batch.drop_constraint('fk_question_versions_canonical_id',type_='foreignkey')
        batch.drop_column('canonical_id')
    op.drop_table('canonical_questions')
