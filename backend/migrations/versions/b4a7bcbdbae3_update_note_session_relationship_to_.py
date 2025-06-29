"""update note session relationship to many to many

Revision ID: b4a7bcbdbae3
Revises: 3cbeed4cb881
Create Date: 2025-06-03 10:53:08.931935

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4a7bcbdbae3'
down_revision = '3cbeed4cb881'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_notes_session_id', table_name='notes')
    op.drop_constraint('notes_session_id_fkey', 'notes', type_='foreignkey')
    op.drop_column('notes', 'session_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('notes', sa.Column('session_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('notes_session_id_fkey', 'notes', 'sessions', ['session_id'], ['id'])
    op.create_index('ix_notes_session_id', 'notes', ['session_id'], unique=False)
    # ### end Alembic commands ### 