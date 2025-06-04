"""rename_conversation_id_to_session_id_in_chat_messages

Revision ID: 4f6d10a3c4c6
Revises: 75736769d677
Create Date: 2025-06-04 10:14:22.520886

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f6d10a3c4c6'
down_revision = '75736769d677'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename conversation_id to session_id in chat_messages table
    op.alter_column('chat_messages', 'conversation_id', new_column_name='session_id')


def downgrade() -> None:
    # Rename session_id back to conversation_id in chat_messages table
    op.alter_column('chat_messages', 'session_id', new_column_name='conversation_id') 