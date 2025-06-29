"""redesign_tool_calls_as_part_of_ai_message

Revision ID: fb1f896c2dc4
Revises: 26d9be805451
Create Date: 2025-05-25 23:50:50.745556

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fb1f896c2dc4'
down_revision = '26d9be805451'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_messages', sa.Column('tool_calls_data', sa.JSON(), nullable=True))
    op.drop_index('ix_chat_messages_agent_id', table_name='chat_messages')
    op.drop_column('chat_messages', 'tool_error')
    op.drop_column('chat_messages', 'tool_calls')
    op.drop_column('chat_messages', 'tool_name')
    op.drop_column('chat_messages', 'tool_result')
    op.drop_column('chat_messages', 'tool_status')
    op.drop_column('chat_messages', 'tool_call_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('chat_messages', sa.Column('tool_call_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('chat_messages', sa.Column('tool_status', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('chat_messages', sa.Column('tool_result', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('chat_messages', sa.Column('tool_name', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('chat_messages', sa.Column('tool_calls', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('chat_messages', sa.Column('tool_error', sa.TEXT(), autoincrement=False, nullable=True))
    op.create_index('ix_chat_messages_agent_id', 'chat_messages', ['agent_id'], unique=False)
    op.drop_column('chat_messages', 'tool_calls_data')
    # ### end Alembic commands ### 